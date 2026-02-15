import json
import os
import time
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

DDB_TABLE = os.environ["DDB_TABLE"]
MODEL_ID = os.environ["BEDROCK_MODEL_ID"]
MEMORY_LIMIT = int(os.environ.get("MEMORY_LIMIT", "10"))

ddb = boto3.resource("dynamodb")
table = ddb.Table(DDB_TABLE)

brt = boto3.client("bedrock-runtime")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resp(status: int, body: dict):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _parse_event(event):
    # HTTP API proxy format: body is a string
    try:
        raw = event.get("body") or "{}"
        data = json.loads(raw) if isinstance(raw, str) else raw
        session_id = (data.get("session_id") or "").strip()
        message = (data.get("message") or "").strip()
        if not session_id:
            session_id = str(uuid.uuid4())
        if not message:
            return None, None, None
        return data, session_id, message
    except Exception:
        return None, None, None


def _fetch_memory(session_id: str):
    # Get last N messages for this session
    resp = table.query(
        KeyConditionExpression=Key("session_id").eq(session_id),
        ScanIndexForward=False,  # newest first
        Limit=MEMORY_LIMIT,
    )
    items = resp.get("Items", [])
    items.reverse()  # oldest -> newest

    # Convert to Bedrock Anthropic messages shape
    messages = []
    for it in items:
        role = it.get("role")
        content = it.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": [{"type": "text", "text": content}]})
    return messages


def _write_message(session_id: str, role: str, content: str, latency_ms: int = None):
    ts = _now_iso()
    item = {
        "session_id": session_id,
        "ts": ts,
        "role": role,
        "content": content,
    }
    if latency_ms is not None:
        item["latency_ms"] = int(latency_ms)
    table.put_item(Item=item)


def _call_bedrock(messages, user_message: str):
    # Convert stored history into Bedrock Converse "messages" format
    convo = []
    for m in messages:
        role = m.get("role")
        content_list = m.get("content", [])
        text = ""
        if isinstance(content_list, list) and content_list:
            first = content_list[0]
            if isinstance(first, dict):
                text = first.get("text", "") or ""
        if role in ("user", "assistant") and text:
            convo.append({"role": role, "content": [{"text": text}]})

    # Add current user message
    convo.append({"role": "user", "content": [{"text": user_message}]})

    t0 = time.time()
    resp = brt.converse(
        modelId=MODEL_ID,
        messages=convo,
        inferenceConfig={
            "maxTokens": 300,
            "temperature": 0.4,
            "topP": 0.9
        },
    )
    latency_ms = int((time.time() - t0) * 1000)

    # Converse response text
    out = ""
    output_msg = resp.get("output", {}).get("message", {})
    content = output_msg.get("content", [])
    if isinstance(content, list) and content:
        out = content[0].get("text", "") or ""

    return out.strip(), latency_ms



def lambda_handler(event, context):
    data, session_id, message = _parse_event(event)
    if not session_id or not message:
        return _resp(400, {"error": "Provide JSON body: { session_id?: string, message: string }"})

    # Fetch memory, call Bedrock, store messages
    memory = _fetch_memory(session_id)

    try:
        _write_message(session_id, "user", message)
        reply, latency_ms = _call_bedrock(memory, message)
        _write_message(session_id, "assistant", reply, latency_ms=latency_ms)

        return _resp(200, {"session_id": session_id, "reply": reply})
    except Exception as e:
        # Log details for debugging (CloudWatch)
        print("ERROR:", str(e))
        return _resp(500, {"error": "Server error", "session_id": session_id})

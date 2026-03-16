import json
import os
import time
import uuid
import traceback
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key


MODEL_ID = os.environ["BEDROCK_MODEL_ID"]
MEMORY_LIMIT = int(os.environ.get("MEMORY_LIMIT", "10"))

MESSAGES_TABLE = os.environ["MESSAGES_TABLE"]
TENANTS_TABLE = os.environ["TENANTS_TABLE"]

dynamodb = boto3.resource("dynamodb")

messages_table = dynamodb.Table(MESSAGES_TABLE)
tenants_table = dynamodb.Table(TENANTS_TABLE)

brt = boto3.client("bedrock-runtime")
bart = boto3.client("bedrock-agent-runtime")


def _get_kb_id_for_tenant(tenant_id: str) -> str:
    resp = tenants_table.get_item(
    Key={"tenant_id": tenant_id},
    ConsistentRead=True
)

    item = resp.get("Item")

    if not item or "knowledge_base_id" not in item:
        raise ValueError(f"No knowledge base configured for tenant: {tenant_id}")

    return item["knowledge_base_id"]


def _has_relevant_retrieval(user_text: str, kb_id: str) -> bool:
    resp = bart.retrieve(
        retrievalQuery={"text": user_text},
        knowledgeBaseId=kb_id,
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": 3
            }
        }
    )

    results = resp.get("retrievalResults", [])
    if not results:
        return False

    combined_text = " ".join(
        r.get("content", {}).get("text", "")
        for r in results
    ).lower()

    query_words = [w.lower() for w in user_text.split() if len(w) > 3]

    matches = sum(1 for w in query_words if w in combined_text)
    return matches >= 1


def kb_answer(user_text: str, tenant_id: str) -> str:
    kb_id = _get_kb_id_for_tenant(tenant_id)
    model_arn = f"arn:aws:bedrock:us-east-1::foundation-model/{MODEL_ID}"

    if not _has_relevant_retrieval(user_text, kb_id):
        return "I couldn't find that in your uploaded documents."

    resp = bart.retrieve_and_generate(
        input={"text": user_text},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": kb_id,
                "modelArn": model_arn
            }
        }
    )

    return resp["output"]["text"]
    

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
        tenant_id = (data.get("tenant_id") or "").strip()  
        message = (data.get("message") or "").strip()
        
        if not session_id:
            session_id = str(uuid.uuid4())
        
        if not message or not tenant_id:
            return None, None, None, None
        
        return data, session_id, tenant_id, message
    
    except Exception:
        return None, None, None, None 


def _fetch_memory(session_id: str):
    pk = f"session#{session_id}"  # match whatever you use when writing messages

    resp = messages_table.query(
        KeyConditionExpression=Key("pk").eq(pk),
        ScanIndexForward=True,      # old→new
        Limit=MEMORY_LIMIT * 2      # optional
    )
    
    return resp.get("Items", [])
    
# Convert to Bedrock Anthropic messages shape
    messages = []
    for it in items:
        role = it.get("role")
        content = it.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": [{"type": "text", "text": content}]})
    return messages


def _write_message(session_id: str, role: str, content: str, latency_ms=None):
    pk = f"session#{session_id}"

    item = {
        "pk": pk,  # REQUIRED
        "ts": str(int(time.time() * 1000)),  # REQUIRED (range key)
        "session_id": session_id,
        "role": role,
        "content": content,
    }

    if latency_ms is not None:
        item["latency_ms"] = latency_ms

    messages_table.put_item(Item=item)


def _call_bedrock(messages, user_message: str, tenant_id: str):    
    t0 = time.time()
    answer = kb_answer(user_message, tenant_id)
    latency_ms = int((time.time() - t0) * 1000)
    return answer, latency_ms



def lambda_handler(event, context):
    session_id = str(uuid.uuid4())

    data, parsed_session_id, tenant_id, message = _parse_event(event)

    if not message or not tenant_id:
        return _resp(400, {"error": "Provide JSON body: { session_id?: string, tenant_id: string, message: string }"})

    if parsed_session_id:
        session_id = parsed_session_id

    try:
        memory = _fetch_memory(session_id)

        _write_message(session_id, "user", message)

        reply, latency_ms = _call_bedrock(memory, message, tenant_id)

        _write_message(session_id, "assistant", reply, latency_ms=latency_ms)

        return _resp(200, {"session_id": session_id, "reply": reply})

    except Exception as e:
        print("🔥 EXCEPTION:", str(e))
        traceback.print_exc()
        return _resp(500, {"error": "Server error", "session_id": session_id})
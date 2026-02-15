🧠 Serverless AI Chatbot on AWS (Terraform + Bedrock)

A production-oriented, serverless chatbot MVP built entirely with Infrastructure as Code (Terraform).

This project demonstrates API design, IAM least privilege, serverless compute, DynamoDB session storage, and Amazon Bedrock integration — along with real-world AWS account gating challenges and graceful degradation patterns.

🏗 Architecture Overview

Frontend

Static single-page HTML app

Hosted in Amazon S3

(CloudFront CDN – pending account verification)


Backend

API Gateway (HTTP API)

AWS Lambda (Python 3.12)

Amazon DynamoDB (chat session memory)


AI Layer

Amazon Bedrock (Nova / Llama models)

On-demand foundation model invocation

Graceful fallback when token quotas unavailable


Infrastructure

Fully provisioned with Terraform

No console click-ops

Environment-based configuration


🔄 Request Flow

User submits message via static HTML frontend.

API Gateway receives POST /chat.

Lambda:

Retrieves session memory from DynamoDB

Calls Amazon Bedrock

Stores updated session state

Response returned to client.

If Bedrock quota is unavailable:

Lambda returns a fallback response

Service remains operational


🔐 Security (MVP vs Production)
MVP (Current)

No authentication

Strict CORS restrictions

IAM least privilege

DynamoDB partition key isolation per session

Production Hardening (Planned)

Amazon Cognito / JWT Authorizer

AWS WAF rate limiting

API Gateway throttling

Structured logging + alarms

CloudFront with HTTPS-only enforcement


📦 Infrastructure as Code

Provisioned using Terraform:

API Gateway HTTP API

Lambda (Python 3.12)

DynamoDB (PAY_PER_REQUEST)

IAM role + inline least-privilege policy

S3 static hosting

(CloudFront CDN – gated)
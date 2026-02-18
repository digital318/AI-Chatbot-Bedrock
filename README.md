# Project Overview

This project is a serverless AI chatbot built on AWS using Amazon Bedrock for LLM inference.  
It demonstrates Infrastructure as Code (Terraform), secure serverless design patterns, and scalable cloud architecture suitable for production environments.


# Live Demo

Frontend (CloudFront):
https://djn6jc1yqeaas.cloudfront.net

API Endpoint:
POST https://b6le5uc3r0.execute-api.us-east-1.amazonaws.com/chat


# Architecture 

The system is designed as a serverless, event-driven architecture:

- Amazon API Gateway (HTTP API) provides a lightweight REST endpoint.
- AWS Lambda (Python 3.12) processes chat requests.
- Amazon DynamoDB stores session-based conversation history.
- Amazon Bedrock powers LLM inference.
- Amazon S3 hosts the static frontend.
- Amazon CloudFront distributes content globally with HTTPS enforcement.


# Architecture Diagram

Client
   ↓
CloudFront
   ↓
S3 (Static Site)
   ↓
API Gateway
   ↓
Lambda
   ↓
Bedrock
   ↓
DynamoDB


# Design Decisions

- Used HTTP API instead of REST API to reduce cost and latency.
- Selected DynamoDB to maintain serverless architecture consistency.
- Implemented environment-based model configuration for flexible LLM switching.
- Managed infrastructure via Terraform to ensure reproducibility.
- Separated application and infrastructure directories for clean DevOps workflows.


# Security Considerations

- IAM role-based access for Lambda
- Principle of least privilege applied to Bedrock and DynamoDB
- HTTPS enforced via CloudFront
- S3 public access blocked


# Current Limitations

- CloudFront distribution pending account verification.
- Bedrock on-demand token quotas restricted on new accounts.


# Request Flow

1. User submits a message from the static frontend (S3).
2. HTTPS request is sent to Amazon API Gateway (HTTP API).
3. API Gateway invokes the Lambda function asynchronously.
4. Lambda:
  - Retrieves conversation history from DynamoDB using session_id
  - Appends new user message
  - Sends structured request to Amazon Bedrock (Converse API)
5. Bedrock returns model response.
6. Lambda:
  - Persists updated conversation history to DynamoDB
  - Returns structured JSON response
7. API Gateway returns response to frontend client.


# Infrastructure as Code

All AWS resources are provisioned using Terraform with environment-based configuration.

Key Components:

- Lambda function (Python 3.12 runtime)
- API Gateway HTTP API
- DynamoDB table (on-demand capacity)
- S3 static hosting bucket
- CloudFront distribution (pending account verification)
- IAM roles with least-privilege Bedrock & DynamoDB access

Design Principles:

- Stateless compute layer (Lambda)
- Session persistence in DynamoDB
- Parameterized model ID via terraform.tfvars
- Environment variable injection into Lambda
- Deterministic builds via archive_file data source
- Reproducible deployment using terraform apply


# Why Serverless?

This project uses a fully serverless architecture to optimize for scalability, cost-efficiency, and operational simplicity.

Design Rationale:

- No server management
AWS Lambda eliminates the need to provision or maintain EC2 instances.

- Automatic scaling
Lambda and API Gateway scale automatically based on request volume.

- Cost efficiency
The system follows a pay-per-request model. With no idle compute resources, costs remain minimal during low usage.

- Event-driven architecture
API Gateway triggers Lambda only when requests are received, aligning with modern cloud-native patterns.

- Stateless compute with persistent storage
Lambda remains stateless while DynamoDB handles session persistence.
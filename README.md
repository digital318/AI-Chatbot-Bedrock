# AI Chatbot Bedrock

A serverless AI chatbot built on AWS using Amazon Bedrock, Lambda, API Gateway, and DynamoDB.
The chatbot supports multi-session conversations, integrates with foundation models from Amazon Bedrock, and can be embedded into websites via a lightweight widget.
This project demonstrates a production-style serverless architecture for building scalable AI applications.


# Project Overview

This project demonstrates a production-ready serverless architecture for building scalable AI chat applications on AWS.  
It uses Amazon Bedrock for AI inference, AWS Lambda for backend logic, API Gateway for REST API exposure, and DynamoDB for session persistence.


# Live Demo

Frontend (CloudFront):
https://djn6jc1yqeaas.cloudfront.net

API Endpoint:
POST https://b6le5uc3r0.execute-api.us-east-1.amazonaws.com/chat


# Architecture 

The system is designed as a serverless, event-driven architecture:

Components:

- Amazon API Gateway (HTTP API) provides a lightweight REST endpoint
- AWS Lambda processes chat requests
- Amazon Bedrock powers LLM inference
- DynamoDB stores session conversation history
- Amazon S3 hosts the static frontend
- CloudFront distributes the application globally


# Architecture Diagram

         
                [ User Browser ]
                        |
                        ▼
                 [ CloudFront ]
                        |
                        ▼
               [ S3 Static Site ]
                (Chat Widget UI)
                        |
                        ▼
                [ API Gateway ]
                   (HTTP API)
                        |
                        ▼
                  [ AWS Lambda ]
                (Chat API Backend)
               |                  |
               ▼                  ▼
        [ Amazon Bedrock ]   [ DynamoDB ]
          (LLM Model)       (Chat Sessions) 


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
- S3 public access blocked with CloudFront as the only distribution layer


# Current Limitations

- No user authentication (public demo only)
- No rate limiting implemented at API Gateway level
- No custom domain (using default CloudFront domain)
- Basic prompt design (no advanced system prompt tuning)
- No structured logging dashboard (CloudWatch only)


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

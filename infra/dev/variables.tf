variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "bedrock-chatbot"
}

variable "bedrock_model_id" {
  type        = string
  description = "Example: anthropic.claude-3-haiku-20240307-v1:0 (must be available in your account/region)"
}

variable "cors_allow_origins" {
  type        = list(string)
  description = "Start with localhost; after first apply, add your CloudFront domain."
  default     = ["http://localhost:5500", "http://localhost:5173", "http://localhost:3000"]
}

variable "memory_limit" {
  type    = number
  default = 10
}

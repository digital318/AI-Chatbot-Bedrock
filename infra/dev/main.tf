locals {
  name_prefix = "${var.project_name}-dev"
}

data "aws_caller_identity" "current" {}

# ---------- DynamoDB ----------
resource "aws_dynamodb_table" "chat_messages" {
  name         = "${local.name_prefix}-messages"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "session_id"
  range_key    = "ts"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "ts"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }
}

# ---------- Lambda package ----------
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../services/chat_api"
  output_path = "${path.module}/build/chat_api.zip"
}

resource "aws_iam_role" "lambda_role" {
  name = "${local.name_prefix}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = { Service = "lambda.amazonaws.com" },
      Action = "sts:AssumeRole"
    }]
  })
}

# Least privilege: DynamoDB + logs + Bedrock invoke on ONE foundation model
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${local.name_prefix}-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      # Logs
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "*"
      },
      # DynamoDB
      {
        Effect = "Allow",
        Action = [
          "dynamodb:PutItem",
          "dynamodb:Query"
        ],
        Resource = aws_dynamodb_table.chat_messages.arn
      },
      # Bedrock InvokeModel on a specific foundation model
      {
        Effect = "Allow",
        Action = [
          "bedrock:InvokeModel",
          "bedrock:Converse",
          "bedrock:ConverseStream"
        ],
  Resource = "arn:aws:bedrock:us-east-1::foundation-model/${var.bedrock_model_id}"
      }
    ]
  })
}

resource "aws_lambda_function" "chat_api" {
  function_name = "${local.name_prefix}-chat-api"
  role          = aws_iam_role.lambda_role.arn
  runtime       = "python3.12"
  handler       = "handler.lambda_handler"

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  timeout      = 20
  memory_size  = 512

  environment {
    variables = {
      DDB_TABLE        = aws_dynamodb_table.chat_messages.name
      BEDROCK_MODEL_ID = var.bedrock_model_id
      MEMORY_LIMIT     = tostring(var.memory_limit)
    }
  }
}

# ---------- API Gateway HTTP API ----------
resource "aws_apigatewayv2_api" "http_api" {
  name          = "${local.name_prefix}-http-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = var.cors_allow_origins
    allow_methods = ["POST", "OPTIONS"]
    allow_headers = ["content-type"]
    max_age       = 3600
  }
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.chat_api.arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "chat_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /chat"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "allow_apigw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.chat_api.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

# ---------- S3 site (private) ----------
resource "aws_s3_bucket" "site" {
  bucket        = "${local.name_prefix}-site-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "site" {
  bucket                  = aws_s3_bucket.site.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "index" {
  bucket       = aws_s3_bucket.site.id
  key          = "index.html"
  source       = "${path.module}/../../site/index.html"
  etag         = filemd5("${path.module}/../../site/index.html")
  content_type = "text/html"
}

# ---------- CloudFront with OAC ----------
resource "aws_cloudfront_origin_access_control" "oac" {
  name                              = "${local.name_prefix}-oac"
  description                       = "OAC for private S3 site"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "cdn" {
  enabled             = true
  default_root_object = "index.html"
  comment             = "${local.name_prefix} static site"

  origin {
    domain_name              = aws_s3_bucket.site.bucket_regional_domain_name
    origin_id                = "s3-site-origin"
    origin_access_control_id = aws_cloudfront_origin_access_control.oac.id
  }

  default_cache_behavior {
    target_origin_id       = "s3-site-origin"
    viewer_protocol_policy = "redirect-to-https"

    allowed_methods = ["GET", "HEAD", "OPTIONS"]
    cached_methods  = ["GET", "HEAD"]

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

resource "aws_s3_bucket_policy" "site_policy" {
  bucket = aws_s3_bucket.site.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Sid    = "AllowCloudFrontServicePrincipalReadOnly",
      Effect = "Allow",
      Principal = { Service = "cloudfront.amazonaws.com" },
      Action = ["s3:GetObject"],
      Resource = "${aws_s3_bucket.site.arn}/*",
      Condition = {
        StringEquals = {
          "AWS:SourceArn" = aws_cloudfront_distribution.cdn.arn
        }
      }
    }]
  })
}

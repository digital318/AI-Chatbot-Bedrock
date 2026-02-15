output "api_endpoint" {
  value = aws_apigatewayv2_api.http_api.api_endpoint
}

output "cloudfront_domain" {
  value = aws_cloudfront_distribution.cdn.domain_name
}

output "site_url" {
  value = "https://${aws_cloudfront_distribution.cdn.domain_name}"
}

output "ddb_table" {
  value = aws_dynamodb_table.chat_messages.name
}

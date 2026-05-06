resource "aws_apigatewayv2_api" "bedrock_proxy" {
  name          = "${local.name_prefix}-bedrock-proxy"
  protocol_type = "HTTP"
  cors_configuration {
    allow_headers = ["content-type", var.bedrock_proxy_required_header, "authorization"]
    allow_methods = ["POST", "OPTIONS"]
    allow_origins = var.api_cors_allowed_origins
    max_age       = 3600
  }
}

resource "aws_apigatewayv2_integration" "bedrock_proxy" {
  api_id                 = aws_apigatewayv2_api.bedrock_proxy.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.bedrock_proxy.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "bedrock_proxy" {
  api_id    = aws_apigatewayv2_api.bedrock_proxy.id
  route_key = "POST /bedrock"
  target    = "integrations/${aws_apigatewayv2_integration.bedrock_proxy.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.bedrock_proxy.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw_bedrock" {
  statement_id  = "AllowAPIGatewayInvokeBedrockProxy"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.bedrock_proxy.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.bedrock_proxy.execution_arn}/*/*"
}

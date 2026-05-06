resource "aws_cloudwatch_event_bus" "central" {
  name = "${local.name_prefix}-central"
}

resource "aws_cloudwatch_event_permission" "allow_org_put_events" {
  event_bus_name = aws_cloudwatch_event_bus.central.name
  statement_id   = "AllowOrgPutEvents"
  action         = "events:PutEvents"
  principal      = "*"
  condition {
    key   = "aws:PrincipalOrgID"
    type  = "StringEquals"
    value = data.aws_organizations_organization.current.id
  }
}

resource "aws_cloudwatch_event_rule" "central_events" {
  name           = "${local.name_prefix}-cloudtrail-events"
  event_bus_name = aws_cloudwatch_event_bus.central.name
  event_pattern = jsonencode({
    "detail-type" = ["AWS API Call via CloudTrail"]
    detail = {
      eventSource = [
        "ec2.amazonaws.com", "sagemaker.amazonaws.com", "lambda.amazonaws.com", "ecs.amazonaws.com", "eks.amazonaws.com",
        "glue.amazonaws.com", "elasticmapreduce.amazonaws.com", "s3.amazonaws.com", "dynamodb.amazonaws.com",
        "bedrock.amazonaws.com", "bedrock-runtime.amazonaws.com", "bedrock-agent.amazonaws.com", "bedrock-agent-runtime.amazonaws.com", "bedrock-agentcore.amazonaws.com"
      ]
    }
  })
}

resource "aws_cloudwatch_event_target" "central_to_sqs" {
  event_bus_name = aws_cloudwatch_event_bus.central.name
  rule           = aws_cloudwatch_event_rule.central_events.name
  arn            = aws_sqs_queue.processor.arn
}

resource "aws_cloudwatch_event_rule" "discovery_schedule" {
  name                = "${local.name_prefix}-discovery-schedule"
  schedule_expression = var.discovery_schedule_expression
}

resource "aws_cloudwatch_event_target" "discovery_lambda" {
  rule = aws_cloudwatch_event_rule.discovery_schedule.name
  arn  = aws_lambda_function.discovery_backfill.arn
}

resource "aws_lambda_permission" "allow_discovery_schedule" {
  statement_id  = "AllowEventBridgeDiscovery"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.discovery_backfill.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.discovery_schedule.arn
}

resource "aws_cloudwatch_event_rule" "daily_reset" {
  name                = "${local.name_prefix}-daily-reset"
  schedule_expression = var.daily_reset_schedule_expression
}

resource "aws_cloudwatch_event_target" "reset_lambda" {
  rule = aws_cloudwatch_event_rule.daily_reset.name
  arn  = aws_lambda_function.reset_budgets.arn
}

resource "aws_lambda_permission" "allow_daily_reset" {
  statement_id  = "AllowEventBridgeReset"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.reset_budgets.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_reset.arn
}

resource "aws_cloudwatch_event_rule" "pricing_schedule" {
  name                = "${local.name_prefix}-pricing-refresh"
  schedule_expression = "cron(0 17 * * ? *)"
}

resource "aws_cloudwatch_event_target" "pricing_lambda" {
  rule = aws_cloudwatch_event_rule.pricing_schedule.name
  arn  = aws_lambda_function.pricing_cache.arn
}

resource "aws_lambda_permission" "allow_pricing_schedule" {
  statement_id  = "AllowEventBridgePricing"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pricing_cache.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.pricing_schedule.arn
}

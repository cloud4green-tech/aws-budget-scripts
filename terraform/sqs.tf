resource "aws_sqs_queue" "processor_dlq" {
  name                      = "${local.name_prefix}-events-dlq"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue" "processor" {
  name                       = "${local.name_prefix}-events"
  visibility_timeout_seconds = 900
  message_retention_seconds  = 345600
  sqs_managed_sse_enabled    = true
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.processor_dlq.arn
    maxReceiveCount     = 5
  })
}

resource "aws_sqs_queue_policy" "allow_eventbridge" {
  queue_url = aws_sqs_queue.processor.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action = "sqs:SendMessage"
      Resource = aws_sqs_queue.processor.arn
      Condition = { ArnEquals = { "aws:SourceArn" = aws_cloudwatch_event_rule.central_events.arn } }
    }]
  })
}

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${local.name_prefix}-dashboard"
  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        x = 0
        y = 0
        width = 12
        height = 6
        properties = {
          title = "Budget Guardian Lambda Errors"
          region = var.management_region
          metrics = [
            ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.event_ingest.function_name],
            ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.discovery_backfill.function_name],
            ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.bedrock_proxy.function_name]
          ]
          stat = "Sum"
          period = 300
        }
      },
      {
        type = "metric"
        x = 12
        y = 0
        width = 12
        height = 6
        properties = {
          title = "Event Queue Depth"
          region = var.management_region
          metrics = [["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", aws_sqs_queue.processor.name]]
          stat = "Average"
          period = 300
        }
      }
    ]
  })
}

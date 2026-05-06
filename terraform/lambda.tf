data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/c4g-budget-guardian.zip"
}

resource "aws_cloudwatch_log_group" "logs" {
  for_each          = toset(["event-ingest", "discovery-backfill", "pricing-cache", "bedrock-proxy", "reset-budgets", "bedrock-price-loader"])
  name              = "/aws/lambda/${local.name_prefix}-${each.key}"
  retention_in_days = 30
}

resource "aws_lambda_function" "event_ingest" {
  function_name    = "${local.name_prefix}-event-ingest"
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.12"
  handler          = "event_ingest.lambda_handler"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 900
  memory_size      = 1024

  environment {
    variables = local.common_env
  }

  depends_on = [aws_cloudwatch_log_group.logs]
}

resource "aws_lambda_function" "discovery_backfill" {
  function_name    = "${local.name_prefix}-discovery-backfill"
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.12"
  handler          = "discovery_backfill.lambda_handler"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 900
  memory_size      = 1024

  environment {
    variables = local.common_env
  }

  depends_on = [aws_cloudwatch_log_group.logs]
}

resource "aws_lambda_function" "pricing_cache" {
  function_name    = "${local.name_prefix}-pricing-cache"
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.12"
  handler          = "pricing_cache.lambda_handler"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 900
  memory_size      = 512

  environment {
    variables = local.common_env
  }

  depends_on = [aws_cloudwatch_log_group.logs]
}

resource "aws_lambda_function" "bedrock_proxy" {
  function_name    = "${local.name_prefix}-bedrock-proxy"
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.12"
  handler          = "bedrock.bedrock_proxy_handler.lambda_handler"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 900
  memory_size      = 1024

  environment {
    variables = local.common_env
  }

  depends_on = [aws_cloudwatch_log_group.logs]
}

resource "aws_lambda_function" "reset_budgets" {
  function_name    = "${local.name_prefix}-reset-budgets"
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.12"
  handler          = "reset_budgets.lambda_handler"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 900
  memory_size      = 512

  environment {
    variables = local.common_env
  }

  depends_on = [aws_cloudwatch_log_group.logs]
}

resource "aws_lambda_function" "bedrock_price_loader" {
  function_name    = "${local.name_prefix}-bedrock-price-loader"
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.12"
  handler          = "bedrock.bedrock_pricing_table_loader.lambda_handler"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 900
  memory_size      = 512

  environment {
    variables = local.common_env
  }

  depends_on = [aws_cloudwatch_log_group.logs]
}

resource "aws_lambda_event_source_mapping" "event_ingest_sqs" {
  event_source_arn                   = aws_sqs_queue.processor.arn
  function_name                      = aws_lambda_function.event_ingest.arn
  batch_size                         = 10
  maximum_batching_window_in_seconds = 5
  function_response_types            = ["ReportBatchItemFailures"]

  scaling_config {
    maximum_concurrency = var.processor_sqs_max_concurrency
  }
}

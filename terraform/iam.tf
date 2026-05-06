data "aws_iam_policy_document" "lambda_assume" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${local.name_prefix}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy" "lambda" {
  name = "${local.name_prefix}-lambda-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "Logs"
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "*"
      },
      {
        Sid    = "DynamoDB"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Scan",
          "dynamodb:Query",
          "dynamodb:BatchWriteItem",
          "dynamodb:TransactWriteItems"
        ]
        Resource = [
          aws_dynamodb_table.users.arn,
          "${aws_dynamodb_table.users.arn}/index/*",
          aws_dynamodb_table.active_resources.arn,
          "${aws_dynamodb_table.active_resources.arn}/index/*",
          aws_dynamodb_table.usage_log.arn,
          aws_dynamodb_table.price_cache.arn,
          aws_dynamodb_table.notification_locks.arn
        ]
      },
      {
        Sid      = "SNS"
        Effect   = "Allow"
        Action   = ["sns:Publish"]
        Resource = aws_sns_topic.alerts.arn
      },
      {
        Sid      = "AssumeMemberRole"
        Effect   = "Allow"
        Action   = ["sts:AssumeRole"]
        Resource = "arn:${data.aws_partition.current.partition}:iam::*:role/${var.member_role_name}"
      },
      {
        Sid    = "OrganizationsSCP"
        Effect = "Allow"
        Action = [
          "organizations:AttachPolicy",
          "organizations:DetachPolicy",
          "organizations:ListTargetsForPolicy",
          "organizations:ListAccountsForParent",
          "organizations:DescribeOrganization"
        ]
        Resource = "*"
      },
      {
        Sid    = "Pricing"
        Effect = "Allow"
        Action = [
          "pricing:GetProducts",
          "pricing:DescribeServices",
          "pricing:GetAttributeValues"
        ]
        Resource = "*"
      },
      {
        Sid    = "BedrockRuntimeProxy"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:CountTokens",
          "bedrock:Converse",
          "bedrock:ConverseStream",
          "bedrock:GetFoundationModel"
        ]
        Resource = "*"
      },
      {
        Sid    = "SQSProcessor"
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility"
        ]
        Resource = aws_sqs_queue.processor.arn
      }
    ]
  })
}

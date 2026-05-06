resource "aws_sns_topic" "alerts" {
  name = "${local.name_prefix}-alerts"
  tags = { System = local.name_prefix }
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

variable "management_region" {
  type    = string
  default = "us-east-1"
}

variable "target_ou_id" {
  type        = string
  description = "OU that contains student accounts."
}

variable "default_budget_usd" {
  type    = number
  default = 2
}

variable "notification_email" {
  type = string
}

variable "pricing_regions" {
  type    = list(string)
  default = ["us-east-1", "us-east-2", "us-west-2", "ap-south-1"]
}

variable "member_role_name" {
  type    = string
  default = "C4GBudgetMemberRole"
}

variable "discovery_schedule_expression" {
  type    = string
  default = "rate(5 minutes)"
}

variable "daily_reset_schedule_expression" {
  type    = string
  default = "cron(30 18 * * ? *)" # midnight IST
}

variable "processor_sqs_max_concurrency" {
  type    = number
  default = 10
}

variable "allow_sagemaker_endpoint_delete" {
  type    = bool
  default = false
}

variable "support_email" {
  type    = string
  default = "labs@cloud4green.com"
}

variable "bedrock_proxy_required_header" {
  type    = string
  default = "x-c4g-user-id"
}

variable "api_cors_allowed_origins" {
  type    = list(string)
  default = ["*"]
}

variable "deploy_member_stackset" {
  type    = bool
  default = true
}

locals {
  name_prefix           = "c4g-budget-guardian"
  default_budget_micros = floor(var.default_budget_usd * 1000000)
  regions_csv           = join(",", var.pricing_regions)
  external_id           = "c4g-${data.aws_caller_identity.current.account_id}-${random_id.suffix.hex}"
  common_env = {
    USERS_TABLE                       = aws_dynamodb_table.users.name
    ACTIVE_RESOURCES_TABLE            = aws_dynamodb_table.active_resources.name
    USAGE_LOG_TABLE                   = aws_dynamodb_table.usage_log.name
    PRICE_CACHE_TABLE                 = aws_dynamodb_table.price_cache.name
    NOTIFICATION_LOCKS_TABLE          = aws_dynamodb_table.notification_locks.name
    SNS_TOPIC_ARN                     = aws_sns_topic.alerts.arn
    MEMBER_ROLE_NAME                  = var.member_role_name
    EXTERNAL_ID                       = local.external_id
    DEFAULT_BUDGET_MICROS             = tostring(local.default_budget_micros)
    MANAGEMENT_REGION                 = var.management_region
    REGIONS                           = local.regions_csv
    PRESTOP_SCP_ID                    = aws_organizations_policy.prestop.id
    HARDLOCK_SCP_ID                   = aws_organizations_policy.hardlock.id
    ALLOW_SAGEMAKER_ENDPOINT_DELETE   = tostring(var.allow_sagemaker_endpoint_delete)
    SUPPORT_EMAIL                     = var.support_email
    BEDROCK_PROXY_REQUIRED_HEADER     = var.bedrock_proxy_required_header
  }
}

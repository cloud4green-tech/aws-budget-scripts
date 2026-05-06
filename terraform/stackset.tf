resource "aws_cloudformation_stack_set" "member_baseline" {
  count            = var.deploy_member_stackset ? 1 : 0
  name             = "${local.name_prefix}-member-baseline"
  permission_model = "SERVICE_MANAGED"
  capabilities     = ["CAPABILITY_NAMED_IAM"]
  auto_deployment {
    enabled                          = true
    retain_stacks_on_account_removal = false
  }
  operation_preferences {
    failure_tolerance_percentage = 10
    max_concurrent_percentage    = 25
  }
  parameters = {
    CentralEventBusArn    = aws_cloudwatch_event_bus.central.arn
    CentralLambdaRoleArn  = aws_iam_role.lambda.arn
    ExternalId            = local.external_id
    MemberRoleName        = var.member_role_name
  }
  template_body = file("${path.module}/member_baseline.yaml")
}

resource "aws_cloudformation_stack_set_instance" "member_baseline_ou" {
  count                  = var.deploy_member_stackset ? 1 : 0
  stack_set_name         = aws_cloudformation_stack_set.member_baseline[0].name
  stack_set_instance_region = var.management_region
  retain_stack           = false
  deployment_targets {
    organizational_unit_ids = [var.target_ou_id]
  }
}

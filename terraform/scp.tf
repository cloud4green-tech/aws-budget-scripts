# 95% SCP: keep students free before threshold. Attach only when threshold is crossed.
# This prevents new spend but still allows read/list/view and safe stop actions.
resource "aws_organizations_policy" "prestop" {
  name        = "${local.name_prefix}-95-prevent-new-spend"
  description = "Attach at 95%. Blocks new spend and writes. Does not delete or terminate resources. Exempts central enforcement role."
  type        = "SERVICE_CONTROL_POLICY"

  content = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyNewHighCostStartsAndInvokes"
        Effect = "Deny"
        Action = [
          "ec2:RunInstances",
          "ec2:StartInstances",
          "ec2:CreateVolume",
          "sagemaker:StartNotebookInstance",
          "sagemaker:CreateTrainingJob",
          "sagemaker:CreateEndpoint",
          "sagemaker:InvokeEndpoint",
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:Converse",
          "bedrock:ConverseStream",
          "bedrock:CreateModelInvocationJob",
          "bedrock:StartAsyncInvoke",
          "lambda:InvokeFunction",
          "lambda:CreateFunction",
          "lambda:UpdateFunctionCode",
          "lambda:UpdateFunctionConfiguration",
          "ecs:RunTask",
          "ecs:StartTask",
          "ecs:CreateService",
          "ecs:UpdateService",
          "eks:CreateCluster",
          "eks:CreateNodegroup",
          "eks:UpdateNodegroupConfig",
          "glue:StartJobRun",
          "elasticmapreduce:RunJobFlow",
          "elasticmapreduce:AddJobFlowSteps",
          "s3:PutObject",
          "s3:PostObject",
          "s3:CreateBucket",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:CreateTable",
          "dynamodb:UpdateTable"
        ]
        Resource = "*"
        Condition = {
          StringNotLike = {
            "aws:PrincipalArn" = ["arn:${data.aws_partition.current.partition}:iam::*:role/${var.member_role_name}"]
          }
        }
      }
    ]
  })
}

# 100% SCP: read-only hard lock for common lab services.
# Avoid broad patterns like *:Get* because many AWS Organizations accounts still reject them in SCP validation.
resource "aws_organizations_policy" "hardlock" {
  name        = "${local.name_prefix}-100-read-only-hard-lock"
  description = "Attach at 100%. Read-only lock for lab services. Exempts central enforcement role for cleanup/reset."
  type        = "SERVICE_CONTROL_POLICY"

  content = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyEverythingExceptReadListViewAndIdentityForLabServices"
        Effect = "Deny"
        NotAction = [
          "account:Get*",
          "aws-portal:View*",
          "billing:Get*",
          "billing:List*",
          "budgets:Describe*",
          "ce:Describe*",
          "ce:Get*",
          "ce:List*",
          "cloudwatch:Describe*",
          "cloudwatch:Get*",
          "cloudwatch:List*",
          "logs:Describe*",
          "logs:FilterLogEvents",
          "logs:Get*",
          "sts:GetCallerIdentity",

          "ec2:Describe*",
          "s3:Get*",
          "s3:List*",
          "dynamodb:BatchGet*",
          "dynamodb:Describe*",
          "dynamodb:Get*",
          "dynamodb:List*",
          "dynamodb:Query",
          "dynamodb:Scan",
          "lambda:Get*",
          "lambda:List*",
          "ecs:Describe*",
          "ecs:List*",
          "eks:Describe*",
          "eks:List*",
          "glue:BatchGet*",
          "glue:Get*",
          "glue:List*",
          "elasticmapreduce:Describe*",
          "elasticmapreduce:List*",
          "sagemaker:Describe*",
          "sagemaker:List*",
          "bedrock:Describe*",
          "bedrock:Get*",
          "bedrock:List*"
        ]
        Resource = "*"
        Condition = {
          StringNotLike = {
            "aws:PrincipalArn" = ["arn:${data.aws_partition.current.partition}:iam::*:role/${var.member_role_name}"]
          }
        }
      }
    ]
  })
}

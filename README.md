# Cloud4Green AWS Budget Guardian

**Status date:** 06/05/2026  
**Owner:** Cloud4Green Technologies  
**Use case:** AWS training lab budget monitoring, Bedrock usage tracking, and safe budget enforcement for student AWS accounts.

---

## Issue / Introduction

Cloud4Green manages AWS training lab accounts for students under an AWS Organizations OU.

Each student account needs a controlled budget, mainly for hands-on Bedrock, Nova, Llama, EC2, SageMaker, Lambda, and other AWS lab usage.

The current requirement is:

```text
Assign $2 budget to each active cloud-user account.
Track usage centrally.
Allow students to use AWS freely before the threshold.
Do not delete or terminate student-created resources.
Stop or block usage only after threshold breach.
```

Students cannot see this custom $2 budget inside their own AWS Billing console because the budget is managed centrally in DynamoDB.

Admins should check budget status from the management account.

---

## Environment

Current environment as of 06/05/2026:

```text
Company: Cloud4Green Technologies
Management account: 969356183753
AWS Organization OU: Cloud4Green Labs
OU ID: ou-qsrf-dt64s7q1
Primary region: us-east-1
Budget amount: $2 per cloud-user account
Budget value in micros: 2000000
Main budget table: c4g-budget-guardian-users
Usage log table: c4g-budget-guardian-usage-log
Active resources table: c4g-budget-guardian-active-resources
Price cache table: c4g-budget-guardian-price-cache
Notification lock table: c4g-budget-guardian-notification-locks
```

Supported student usage:

```text
Amazon Bedrock
Amazon Nova models
Meta Llama models
Amazon Titan models
EC2
SageMaker
Lambda
ECS
EKS
S3
DynamoDB
Glue
EMR
CloudWatch
```

Allowed Bedrock regions:

```text
us-east-1
us-east-2
us-west-1
us-west-2
ap-south-1
```

---

## Cause

During the earlier training program, Cloud4Green did not have enough budget control across student AWS accounts.

Some accounts continued running services overnight, which caused the AWS cost to spike unexpectedly.

To avoid the same issue in the current program, Cloud4Green added a centralized $2 budget control for all required student accounts.

The goal is to:

```text
Track usage centrally.
Assign budget before students start labs.
Warn at 80% usage.
Take safe pre-stop action at 95%.
Apply hard lock at 100%.
Avoid overnight cost spikes.
Protect student work by stopping only, not deleting or terminating.
```

Common technical causes seen during setup:

### 1. Budget table mismatch

Earlier, some budgets were added to:

```text
c4g-budget-users
```

But the live system uses:

```text
c4g-budget-guardian-users
```

If budgets are not in `c4g-budget-guardian-users`, usage tracking and enforcement may not work correctly.

### 2. Student cannot see budget in AWS Console

This is expected.

The $2 budget is a custom DynamoDB-based budget, not an AWS native Budget created inside the student account.

Students will not see it under:

```text
Billing and Cost Management → Budgets
```

### 3. Bedrock AccessDenied despite AdministratorAccess

AdministratorAccess does not override explicit deny.

If a student sees:

```text
explicit deny in an identity-based policy
```

then an inline policy or permission set deny is blocking the request.

A common cause is a region deny policy that does not allow Bedrock global or cross-region model calls.

### 4. Usage log is empty

If students are using Bedrock but `c4g-budget-guardian-usage-log` is empty, possible reasons are:

```text
Student account is missing from c4g-budget-guardian-users
Students are using direct Bedrock Console instead of the Bedrock proxy
StackSet baseline is not active for that account
EventBridge forwarding is not active
CloudTrail events are delayed
Event ingest Lambda is failing or ignoring events
```

### 5. Direct Bedrock Console tracking is not perfect real-time

Real-time token reserve and refund works best through the Bedrock proxy.

Direct console usage depends on CloudTrail, EventBridge, CloudWatch, and scheduled discovery/backfill.

---

## Resolution

### 1. Confirm correct AWS profile

```powershell
$env:AWS_PROFILE="sharadha-root"
$env:AWS_PAGER=""

aws sts get-caller-identity
```

Expected account:

```text
969356183753
```

### 2. Check budget tables

```powershell
aws dynamodb list-tables `
  --query "TableNames[?contains(@,'c4g-budget')]" `
  --output table `
  --region us-east-1 `
  --no-cli-pager
```

Main live table:

```text
c4g-budget-guardian-users
```

### 3. Verify $2 budget assignment

```powershell
aws dynamodb scan `
  --table-name c4g-budget-guardian-users `
  --query "Items[*].[account_id.S,budget_total_micros.N,budget_used_micros.N,threshold_state.S]" `
  --output table `
  --region us-east-1 `
  --no-cli-pager
```

Expected:

```text
budget_total_micros = 2000000
threshold_state     = OPEN
```

### 4. Add $2 budget to selected accounts

```powershell
$accountCsv="809411919736,225119180544,720115910112"

python ..\scripts\init_budgets.py `
  --table c4g-budget-guardian-users `
  --budget-usd 2 `
  --accounts $accountCsv
```

### 5. Check accounts with usage

```powershell
$data = aws dynamodb scan `
  --table-name c4g-budget-guardian-users `
  --output json `
  --region us-east-1 `
  --no-cli-pager | ConvertFrom-Json

$data.Items |
  Where-Object { [int64]$_.budget_used_micros.N -gt 0 } |
  Select-Object `
    @{Name="AccountId";Expression={$_.account_id.S}},
    @{Name="BudgetUSD";Expression={[decimal]$_.budget_total_micros.N / 1000000}},
    @{Name="UsedUSD";Expression={[decimal]$_.budget_used_micros.N / 1000000}},
    @{Name="RemainingUSD";Expression={([decimal]$_.budget_total_micros.N - [decimal]$_.budget_used_micros.N) / 1000000}},
    @{Name="Status";Expression={$_.threshold_state.S}} |
  Format-Table -Auto
```

### 6. Check usage log

```powershell
aws dynamodb scan `
  --table-name c4g-budget-guardian-usage-log `
  --output table `
  --region us-east-1 `
  --no-cli-pager
```

### 7. Check Lambda logs

```powershell
aws logs tail /aws/lambda/c4g-budget-guardian-event-ingest `
  --since 1h `
  --region us-east-1 `
  --no-cli-pager
```

```powershell
aws logs tail /aws/lambda/c4g-budget-guardian-discovery-backfill `
  --since 1h `
  --region us-east-1 `
  --no-cli-pager
```

```powershell
aws logs tail /aws/lambda/c4g-budget-guardian-bedrock-proxy `
  --since 1h `
  --region us-east-1 `
  --no-cli-pager
```

### 8. Fix Bedrock inline permission issue

Use AdministratorAccess with an inline deny policy that still allows Bedrock across required regions.

Important:

```text
Do not let the region deny block Bedrock runtime actions.
Explicit deny overrides AdministratorAccess.
```

After updating IAM Identity Center permission sets, provision the permission set again and ask students to sign out and sign in again.

---

## Additional Information

### Budget micros conversion

```text
$2.00 = 2000000 micros
$1.60 = 1600000 micros
$1.90 = 1900000 micros
300 micros = $0.000300
```

### Student visibility

Students cannot see the custom budget in the AWS Billing console.

Admin must check budget in:

```text
DynamoDB → c4g-budget-guardian-users
```

A student-facing LMS or lab portal page can be added later.

### Bedrock model access

Students may need:

```text
AmazonBedrockFullAccess
Bedrock model access enabled
Marketplace permissions for some third-party models
Allowed regions configured correctly
```

Required Bedrock-related permissions:

```text
bedrock:*
bedrock-runtime:*
bedrock-agent:*
bedrock-agent-runtime:*
bedrock-data-automation:*
bedrock-data-automation-runtime:*
aws-marketplace:ViewSubscriptions
aws-marketplace:Subscribe
aws-marketplace:Unsubscribe
```

### Safe enforcement rules

The platform must never delete or terminate student work.

Allowed:

```text
Stop EC2
Stop SageMaker notebooks
Stop jobs where supported
Scale ECS services to 0
Scale EKS node groups to 0
Disable Lambda triggers
Block new write/start/invoke actions after threshold
```

Not allowed:

```text
Terminate EC2
Delete S3 objects
Delete DynamoDB tables
Delete Lambda functions
Delete SageMaker endpoints
Delete Bedrock resources
Delete EKS clusters
```

### Best practice

Use Bedrock proxy for accurate real-time token cost tracking.

Direct Bedrock Console usage can still be monitored, but it may not provide the same real-time reserve/refund accuracy.

---

## 1. Overview

Cloud4Green AWS Budget Guardian is an internal AWS governance platform for managing student lab accounts under AWS Organizations.

It is designed for training environments where students need hands-on AWS access, but Cloud4Green still needs strong budget control.

The system assigns a fixed budget to student accounts, tracks estimated usage, logs activity, and applies safe stop or block actions when usage crosses the configured threshold.

---

## 2. Current Budget Policy

Each student account is assigned:

```text
$2.00 budget
```

The system stores budget in micros.

```text
$2.00 = 2,000,000 micros
```

Thresholds:

| Threshold | Amount | Action |
|---|---:|---|
| 80% | $1.60 | Warning only |
| 95% | $1.90 | Pre-stop / prevent additional spend |
| 100% | $2.00 | Hard lock / read-only mode |

---

## 3. Student Access Rule

Students should have free access before they reach the budget threshold.

Do not deny services at the start.

Allowed before threshold:

```text
Amazon Bedrock
Amazon Nova models
Meta Llama models
Amazon Titan models
SageMaker
EC2
Lambda
ECS
EKS
S3
DynamoDB
Glue
EMR
CloudWatch
IAM lab-level usage
```

Restrictions should start only after budget threshold is reached.

---

## 4. No Delete / No Terminate Rule

The system must never delete or terminate student work.

### Allowed Safe Actions

```text
Stop EC2 instances
Stop SageMaker notebooks
Stop supported jobs
Disable Lambda triggers
Set Lambda reserved concurrency to 0
Scale ECS services to 0
Scale EKS managed node groups down safely
Block new Bedrock inference after threshold
Block write/start/invoke actions after hard lock
Allow read/list/view access after hard lock
```

### Not Allowed

```text
Do not terminate EC2 instances
Do not delete SageMaker notebooks
Do not delete SageMaker endpoints
Do not delete Bedrock agents
Do not delete Bedrock knowledge bases
Do not delete Bedrock guardrails
Do not delete Bedrock prompts
Do not delete S3 buckets or objects
Do not delete DynamoDB tables or data
Do not delete Lambda functions
Do not delete ECS or EKS resources
Do not delete student-created artifacts
```

---

## 5. Architecture

The platform uses:

```text
AWS Organizations
AWS IAM Identity Center
CloudFormation StackSets
Terraform
DynamoDB
Lambda
EventBridge
CloudTrail
CloudWatch Logs
SNS
SQS
API Gateway
Amazon Bedrock Runtime
AWS Pricing API
```

High-level flow:

```text
Student uses AWS
        |
CloudTrail / EventBridge captures activity
        |
Central EventBridge bus
        |
SQS queue
        |
Lambda event processor
        |
DynamoDB budget tables
        |
Threshold handler
        |
SNS notification / safe enforcement
```

For Bedrock proxy calls:

```text
Student request
        |
API Gateway Bedrock proxy
        |
CountTokens
        |
Reserve estimated cost in DynamoDB
        |
Call Bedrock
        |
Read actual token usage
        |
Deduct actual cost
        |
Refund unused reservation
        |
Trigger threshold actions if needed
```

---

## 6. Main DynamoDB Tables

### Main Budget Table

```text
c4g-budget-guardian-users
```

Important fields:

```text
user_id
account_id
email
budget_total_micros
budget_used_micros
projected_used_micros
reserved_micros
threshold_state
threshold_level
created_at
updated_at
```

For a valid $2 budget row:

```text
budget_total_micros = 2000000
budget_used_micros  = 0
threshold_state     = OPEN
```

### Usage Log Table

```text
c4g-budget-guardian-usage-log
```

Stores activity and estimated cost deductions.

### Active Resources Table

```text
c4g-budget-guardian-active-resources
```

Stores discovered running resources.

### Price Cache Table

```text
c4g-budget-guardian-price-cache
```

Stores cached pricing data.

### Notification Lock Table

```text
c4g-budget-guardian-notification-locks
```

Prevents duplicate 80%, 95%, and 100% alerts.

---

## 7. Repository Structure

```text
bedrock-budget-v2/
  README.md

  terraform/
    apigateway.tf
    cloudtrail.tf
    dashboard.tf
    dynamodb.tf
    eventbridge.tf
    iam.tf
    lambda.tf
    locals.tf
    member_baseline.yaml
    outputs.tf
    scp.tf
    sns.tf
    sqs.tf
    stackset.tf
    terraform.tfvars.example
    variables.tf
    versions.tf

  src/
    budget_manager.py
    cost_engine.py
    discovery_backfill.py
    enforcement_engine.py
    event_ingest.py
    pricing_cache.py
    reset_budgets.py
    sns_notifier.py
    threshold_handler.py

  src/bedrock/
    bedrock_proxy_handler.py
    bedrock_cost_calculator.py
    bedrock_pricing_table_loader.py
    bedrock_activity_mapper.py
    bedrock_token_usage_parser.py

  src/service_handlers/
    ec2_handler.py
    sagemaker_handler.py
    lambda_handler.py
    ecs_handler.py
    eks_handler.py
    glue_handler.py
    emr_handler.py
    s3_handler.py
    dynamodb_handler.py
    bedrock_handler.py

  scripts/
    deploy.ps1
    destroy.ps1
    init_users.ps1
    init_budgets.py
    refresh_budget_table.ps1
    discover_existing_resources.ps1
    test_bedrock_proxy.ps1
    test_ec2_tracking.ps1

  docs/
    architecture.md
    bedrock_coverage.md
    deployment_guide.md
    testing_guide.md
    troubleshooting.md
    student_usage_guide.md
    admin_operations.md
```

---

## 8. Prerequisites

Required tools:

```text
AWS CLI v2
Terraform
Python 3.10+
PowerShell
boto3
```

Install boto3 if needed:

```powershell
pip install boto3
```

Set AWS profile:

```powershell
$env:AWS_PROFILE="sharadha-root"
$env:AWS_PAGER=""

aws sts get-caller-identity
```

Expected management account:

```text
969356183753
```

---

## 9. Terraform Configuration

Go to Terraform folder:

```powershell
cd C:\Users\Admin\Downloads\bedrock-budget-v2\terraform
```

Create tfvars:

```powershell
copy terraform.tfvars.example terraform.tfvars
notepad terraform.tfvars
```

Recommended values as of 06/05/2026:

```hcl
management_region  = "us-east-1"
target_ou_id       = "ou-qsrf-dt64s7q1"
default_budget_usd = 2
notification_email = "lohit@cloud4green.com"

pricing_regions = [
  "us-east-1",
  "us-east-2",
  "us-west-1",
  "us-west-2",
  "ap-south-1"
]
```

---

## 10. Enable StackSet Access

Run once from the management account:

```powershell
aws cloudformation activate-organizations-access
aws cloudformation describe-organizations-access
```

Expected:

```json
{
  "Status": "ENABLED"
}
```

---

## 11. Deploy

```powershell
terraform init
terraform validate
terraform plan -out=tfplan
terraform apply "tfplan"
```

If Terraform times out during StackSet creation, check operation status:

```powershell
$opId = aws cloudformation list-stack-set-operations `
  --stack-set-name c4g-budget-guardian-member-baseline `
  --region us-east-1 `
  --query "Summaries[0].OperationId" `
  --output text `
  --no-cli-pager

aws cloudformation describe-stack-set-operation `
  --stack-set-name c4g-budget-guardian-member-baseline `
  --operation-id $opId `
  --region us-east-1 `
  --query "StackSetOperation.[OperationId,Action,Status,StatusReason]" `
  --output table `
  --no-cli-pager
```

Count status:

```powershell
$results = aws cloudformation list-stack-set-operation-results `
  --stack-set-name c4g-budget-guardian-member-baseline `
  --operation-id $opId `
  --region us-east-1 `
  --output json `
  --no-cli-pager | ConvertFrom-Json

$results.Summaries | Group-Object Status | Select-Object Name,Count
```

---

## 12. Assign $2 Budget to Cloud User Accounts

The main budget table is:

```text
c4g-budget-guardian-users
```

The cloud-user batch includes accounts such as:

```text
cloud-user0@cloud4green.com
cloud-user1@cloud4green.com
...
cloud-user48@cloud4green.com
```

These accounts map to AWS account IDs under:

```text
Cloud4Green Labs
ou-qsrf-dt64s7q1
```

Example command to initialize specific account IDs:

```powershell
$accountCsv="809411919736,225119180544,720115910112"

python ..\scripts\init_budgets.py `
  --table c4g-budget-guardian-users `
  --budget-usd 2 `
  --accounts $accountCsv
```

---

## 13. Check Budget Status

```powershell
aws dynamodb scan `
  --table-name c4g-budget-guardian-users `
  --query "Items[*].[account_id.S,budget_total_micros.N,budget_used_micros.N,threshold_state.S]" `
  --output table `
  --region us-east-1 `
  --no-cli-pager
```

Expected:

```text
account_id        budget_total_micros   budget_used_micros   threshold_state
809411919736      2000000               0                    OPEN
```

---

## 14. Check Only Accounts With Usage

PowerShell sometimes breaks inline JSON for AWS CLI. Use PowerShell object filtering instead:

```powershell
$data = aws dynamodb scan `
  --table-name c4g-budget-guardian-users `
  --output json `
  --region us-east-1 `
  --no-cli-pager | ConvertFrom-Json

$data.Items |
  Where-Object { [int64]$_.budget_used_micros.N -gt 0 } |
  Select-Object `
    @{Name="AccountId";Expression={$_.account_id.S}},
    @{Name="BudgetUSD";Expression={[decimal]$_.budget_total_micros.N / 1000000}},
    @{Name="UsedUSD";Expression={[decimal]$_.budget_used_micros.N / 1000000}},
    @{Name="RemainingUSD";Expression={([decimal]$_.budget_total_micros.N - [decimal]$_.budget_used_micros.N) / 1000000}},
    @{Name="Status";Expression={$_.threshold_state.S}} |
  Format-Table -Auto
```

Example conversion:

```text
300 micros = $0.000300
2000000 micros = $2.00
```

---

## 15. Check Usage Logs

```powershell
aws dynamodb scan `
  --table-name c4g-budget-guardian-usage-log `
  --output table `
  --region us-east-1 `
  --no-cli-pager
```

For one account:

```powershell
$ACCOUNT_ID="809411919736"

$data = aws dynamodb scan `
  --table-name c4g-budget-guardian-usage-log `
  --output json `
  --region us-east-1 `
  --no-cli-pager | ConvertFrom-Json

$data.Items |
  Where-Object { $_.account_id.S -eq $ACCOUNT_ID } |
  Select-Object `
    @{Name="AccountId";Expression={$_.account_id.S}},
    @{Name="Service";Expression={$_.service.S}},
    @{Name="Event";Expression={$_.event_name.S}},
    @{Name="CostUSD";Expression={[decimal]$_.cost_delta_micros.N / 1000000}},
    @{Name="Time";Expression={$_.timestamp.S}} |
  Format-Table -Auto
```

---

## 16. Check Active Resources

```powershell
aws dynamodb scan `
  --table-name c4g-budget-guardian-active-resources `
  --output table `
  --region us-east-1 `
  --no-cli-pager
```

---

## 17. Check CloudWatch Logs

List Lambda log groups:

```powershell
aws logs describe-log-groups `
  --log-group-name-prefix "/aws/lambda/c4g-budget-guardian" `
  --query "logGroups[*].logGroupName" `
  --output table `
  --region us-east-1 `
  --no-cli-pager
```

Event ingest logs:

```powershell
aws logs tail /aws/lambda/c4g-budget-guardian-event-ingest `
  --since 1h `
  --region us-east-1 `
  --no-cli-pager
```

Discovery logs:

```powershell
aws logs tail /aws/lambda/c4g-budget-guardian-discovery-backfill `
  --since 1h `
  --region us-east-1 `
  --no-cli-pager
```

Bedrock proxy logs:

```powershell
aws logs tail /aws/lambda/c4g-budget-guardian-bedrock-proxy `
  --since 1h `
  --region us-east-1 `
  --no-cli-pager
```

---

## 18. Bedrock Access Notes

Students may have AdministratorAccess, but Bedrock can still fail due to explicit deny policies.

If students see:

```text
explicit deny in an identity-based policy
```

check the inline policy attached to the IAM Identity Center permission set.

Allowed Bedrock regions:

```text
us-east-1
us-east-2
us-west-1
us-west-2
ap-south-1
```

Recommended Bedrock permissions:

```text
bedrock:*
bedrock-runtime:*
bedrock-agent:*
bedrock-agent-runtime:*
bedrock-data-automation:*
bedrock-data-automation-runtime:*
aws-marketplace:ViewSubscriptions
aws-marketplace:Subscribe
aws-marketplace:Unsubscribe
```

---

## 19. Recommended Inline Policy for Students

Use this with AdministratorAccess when you want to block billing/org access but allow Bedrock across selected regions.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyBillingAndAccount",
      "Effect": "Deny",
      "Action": [
        "aws-portal:*",
        "billing:*",
        "ce:*",
        "cur:*",
        "budgets:*",
        "payments:*",
        "account:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DenyOrgAndAccountManagement",
      "Effect": "Deny",
      "Action": [
        "organizations:*",
        "support:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DenySensitiveIAM",
      "Effect": "Deny",
      "Action": [
        "iam:DeleteAccountPasswordPolicy",
        "iam:UpdateAccountPasswordPolicy",
        "iam:CreateAccountAlias",
        "iam:DeleteAccountAlias",
        "iam:UpdateAccountName"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DenyAllRegionsExceptAllowedButAllowBedrock",
      "Effect": "Deny",
      "NotAction": [
        "bedrock:*",
        "bedrock-runtime:*",
        "bedrock-agent:*",
        "bedrock-agent-runtime:*",
        "bedrock-data-automation:*",
        "bedrock-data-automation-runtime:*",
        "aws-marketplace:ViewSubscriptions",
        "aws-marketplace:Subscribe",
        "aws-marketplace:Unsubscribe",
        "sts:GetCallerIdentity",
        "iam:GetRole",
        "iam:ListRoles",
        "iam:PassRole"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": [
            "us-east-1",
            "us-east-2",
            "us-west-1",
            "us-west-2",
            "ap-south-1"
          ]
        }
      }
    }
  ]
}
```

After changing an IAM Identity Center permission set, provision it again to target accounts.

---

## 20. Test Bedrock Models

List available Nova, Amazon, and Llama models:

```bash
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query "modelSummaries[?contains(modelId,'llama') || contains(modelId,'nova') || contains(modelId,'amazon')].[modelId,providerName]" \
  --output table \
  --no-cli-pager
```

Test Nova:

```bash
aws bedrock-runtime converse \
  --model-id amazon.nova-lite-v1:0 \
  --messages '[{"role":"user","content":[{"text":"Say hello in one short sentence"}]}]' \
  --inference-config '{"maxTokens":100,"temperature":0.2}' \
  --region us-east-1 \
  --no-cli-pager
```

Test Llama:

```bash
aws bedrock-runtime converse \
  --model-id meta.llama3-8b-instruct-v1:0 \
  --messages '[{"role":"user","content":[{"text":"Say hello in one short sentence"}]}]' \
  --inference-config '{"maxTokens":100,"temperature":0.2}' \
  --region us-east-1 \
  --no-cli-pager
```

---

## 21. Student Console Visibility

Students cannot see this custom $2 budget in the AWS Billing console.

The budget is stored centrally in DynamoDB:

```text
c4g-budget-guardian-users
```

Admin can check it from:

```text
DynamoDB → Tables → c4g-budget-guardian-users → Explore table items
```

A student-facing LMS or lab portal page should be created later to show:

```text
Assigned budget
Used amount
Remaining amount
Status
```

---

## 22. Emergency Stop Rules

Emergency stop should be safe.

Allowed:

```text
Stop EC2
Stop SageMaker notebooks
Stop supported jobs
Scale ECS services to 0
Scale EKS node groups to 0
Disable Lambda event triggers
Set Lambda concurrency to 0
```

Not allowed:

```text
Terminate EC2
Delete S3 data
Delete DynamoDB tables
Delete Lambda functions
Delete SageMaker endpoints
Delete Bedrock resources
Delete EKS clusters
```

---

## 23. Troubleshooting

### Table Not Found

Confirm profile:

```powershell
aws sts get-caller-identity
```

Expected account:

```text
969356183753
```

List budget tables:

```powershell
aws dynamodb list-tables `
  --query "TableNames[?contains(@,'c4g-budget')]" `
  --output table `
  --region us-east-1 `
  --no-cli-pager
```

### Usage Log Is Empty

Check:

```text
1. Is the account present in c4g-budget-guardian-users?
2. Are students using direct Bedrock Console instead of the proxy?
3. Is StackSet baseline active?
4. Is EventBridge forwarding active?
5. Is event-ingest Lambda running?
6. Are Lambda logs showing ignored or failed events?
```

### Student Gets Bedrock AccessDenied

Check:

```text
1. SCP attached to the account
2. IAM Identity Center permission set
3. Inline explicit deny policy
4. Region deny condition
5. Bedrock model access
6. AWS Marketplace model permission
```

### StackSet Takes Too Long

Check operation status:

```powershell
$opId = aws cloudformation list-stack-set-operations `
  --stack-set-name c4g-budget-guardian-member-baseline `
  --region us-east-1 `
  --query "Summaries[0].OperationId" `
  --output text `
  --no-cli-pager

aws cloudformation describe-stack-set-operation `
  --stack-set-name c4g-budget-guardian-member-baseline `
  --operation-id $opId `
  --region us-east-1 `
  --query "StackSetOperation.[OperationId,Action,Status,StatusReason]" `
  --output table `
  --no-cli-pager
```

---

## 24. Current Known State as of 06/05/2026

```text
Management account: 969356183753
OU: Cloud4Green Labs
OU ID: ou-qsrf-dt64s7q1
Primary region: us-east-1
Budget table: c4g-budget-guardian-users
Budget amount: $2 per cloud-user account
Budget micros value: 2000000
Bedrock focus: Nova, Llama, Amazon/Titan models
Student model access: Requires IAM + Bedrock model access
Student budget visibility: Admin-only through DynamoDB
Delete/terminate policy: Not allowed
```

---

## 25. Important Notes

1. DynamoDB budget rows confirm budget assignment.
2. StackSet baseline is required for full event forwarding and enforcement.
3. Direct Bedrock Console usage may not give perfect real-time token costing.
4. Bedrock proxy is required for the most accurate real-time token reserve/refund flow.
5. AWS model token limits and service quotas still apply.
6. Explicit deny always overrides AdministratorAccess.
7. After IAM Identity Center permission set changes, students must sign out and sign in again.

---

## 26. License

Internal use only.

Cloud4Green Technologies.

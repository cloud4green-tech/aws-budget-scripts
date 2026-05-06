# Deployment Guide

## Prerequisites

- AWS CLI configured for the AWS Organizations management account
- Terraform 1.6+
- Python 3.10+
- Organization all-features enabled
- SCPs enabled
- StackSets trusted access enabled

## Deploy

```powershell
cd terraform
copy terraform.tfvars.example terraform.tfvars
notepad terraform.tfvars
aws cloudformation activate-organizations-access
terraform init
terraform validate
terraform plan -out=tfplan
terraform apply "tfplan"
```

## Load price cache

```powershell
$pricing = terraform output -raw pricing_lambda_name
aws lambda invoke --function-name $pricing --cli-binary-format raw-in-base64-out --payload "{}" pricing-output.json
```

## Initialize users

```powershell
..\scripts\init_users.ps1
```

## Confirm email

Open the SNS email and confirm the subscription.

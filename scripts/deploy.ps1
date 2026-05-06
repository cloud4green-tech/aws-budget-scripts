$ErrorActionPreference = "Stop"
$env:AWS_PAGER = ""
cd "$PSScriptRoot\..\terraform"
aws sts get-caller-identity
aws cloudformation activate-organizations-access
copy terraform.tfvars.example terraform.tfvars -ErrorAction SilentlyContinue
Write-Host "Edit terraform.tfvars before continuing." -ForegroundColor Yellow
notepad terraform.tfvars
terraform init
terraform validate
terraform plan -out=tfplan
terraform apply "tfplan"
$pricing = terraform output -raw pricing_lambda_name
aws lambda invoke --function-name $pricing --cli-binary-format raw-in-base64-out --payload "{}" pricing-output.json --no-cli-pager
Write-Host "Confirm the SNS email subscription." -ForegroundColor Yellow
terraform output

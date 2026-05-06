$ErrorActionPreference = "Stop"
$env:AWS_PAGER = ""
cd "$PSScriptRoot\..\terraform"
aws sts get-caller-identity
terraform destroy

$ErrorActionPreference = "Stop"
$env:AWS_PAGER = ""
cd "$PSScriptRoot\..\terraform"
$fn = terraform output -raw discovery_lambda_name
aws lambda invoke --function-name $fn --cli-binary-format raw-in-base64-out --payload "{}" discovery-output.json --no-cli-pager
type discovery-output.json

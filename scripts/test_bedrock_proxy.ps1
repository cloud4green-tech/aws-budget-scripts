$ErrorActionPreference = "Stop"
$env:AWS_PAGER = ""
cd "$PSScriptRoot\..\terraform"
$url = terraform output -raw bedrock_proxy_url
$body = @{
  operation = "Converse"
  region = "us-east-1"
  modelId = "amazon.nova-micro-v1:0"
  messages = @(@{ role = "user"; content = @(@{ text = "Say hello in one sentence." }) })
  inferenceConfig = @{ maxTokens = 50 }
} | ConvertTo-Json -Depth 10
Invoke-RestMethod -Method POST -Uri $url -Headers @{"x-c4g-user-id"="student-REPLACE_ACCOUNT_ID"} -ContentType "application/json" -Body $body

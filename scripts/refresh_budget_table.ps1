$ErrorActionPreference = "Stop"
$env:AWS_PAGER = ""
param([double]$BudgetUsd = 2)
cd "$PSScriptRoot\..\terraform"
$OU_ID = (Select-String -Path .\terraform.tfvars -Pattern 'target_ou_id').ToString().Split('=')[1].Trim().Trim('"')
$TABLE = terraform output -raw users_table
$accounts = aws organizations list-accounts-for-parent --parent-id $OU_ID --query "Accounts[?Status=='ACTIVE'].Id" --output text --no-cli-pager
$accountCsv = (($accounts -split "\s+") | Where-Object { $_ }) -join ","
python ..\scripts\init_budgets.py --table $TABLE --budget-usd $BudgetUsd --accounts $accountCsv

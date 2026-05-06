# Testing Guide

## Test Bedrock proxy

Edit `scripts/test_bedrock_proxy.ps1` and replace `student-REPLACE_ACCOUNT_ID` with a real user ID.

```powershell
..\scripts\test_bedrock_proxy.ps1
```

## Test discovery

```powershell
..\scripts\discover_existing_resources.ps1
```

## Test EC2 tracking

Launch a small EC2 instance in a student account. Wait up to 5 minutes or invoke discovery manually.

```powershell
..\scripts\test_ec2_tracking.ps1
```

## Verify budgets

```powershell
aws dynamodb scan --table-name c4g-budget-guardian-users --query "Items[*].[user_id.S,account_id.S,budget_total_micros.N,budget_used_micros.N,threshold_state.S]" --output table
```

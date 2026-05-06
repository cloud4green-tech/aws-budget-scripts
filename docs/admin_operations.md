# Admin Operations

## Reset all budgets to $2

```powershell
..\scripts\refresh_budget_table.ps1 -BudgetUsd 2
```

## Run discovery now

```powershell
..\scripts\discover_existing_resources.ps1
```

## Detach SCP manually

```powershell
aws organizations detach-policy --policy-id POLICY_ID --target-id ACCOUNT_ID
```

## Check attached SCPs

```powershell
aws organizations list-policies-for-target --target-id ACCOUNT_ID --filter SERVICE_CONTROL_POLICY --output table
```

## Never run delete cleanup from member accounts

All operations must run from the management account.

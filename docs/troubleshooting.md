# Troubleshooting

## Student sees AccessDenied before using budget

Check if an SCP was manually attached.

```powershell
aws organizations list-policies-for-target --target-id ACCOUNT_ID --filter SERVICE_CONTROL_POLICY --output table
```

Students should not have the 95% or 100% SCP attached at the start.

## Bedrock proxy says budget not found

Make sure the user row exists in the users table and the request header has `x-c4g-user-id`.

## Direct Bedrock calls are not exact

Use the Bedrock proxy for exact reserve/refund control. Direct console/CLI calls are estimated from CloudTrail because token usage is not always in CloudTrail.

## StackSet failures

Check:

```powershell
aws cloudformation list-stack-set-operation-results --stack-set-name c4g-budget-guardian-member-baseline --operation-id OP_ID --output table
```

## S3 bucket delete fails during destroy

Empty versioned objects from the CloudTrail bucket first.

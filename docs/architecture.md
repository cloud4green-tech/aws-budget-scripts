# Architecture

Cloud4Green Budget Guardian v2 uses:

- AWS Organizations and OU-based student account structure
- CloudFormation StackSets for member-account baseline
- Organization CloudTrail and member EventBridge forwarding
- Central EventBridge bus + SQS + Lambda processor
- DynamoDB for budget, active resource, usage log, pricing cache, and notification locks
- API Gateway Bedrock proxy for friendly budget-aware Bedrock access
- Scheduled discovery/backfill Lambda every 5 minutes
- SNS notifications
- SCPs attached only at 95% and 100%

## Flow

1. Student starts with free AWS access.
2. API activity arrives via CloudTrail/EventBridge.
3. Discovery Lambda scans already-running resources.
4. Bedrock proxy reserves and refunds budget with token-aware calculation.
5. Budget is stored in DynamoDB in micros.
6. Threshold handler evaluates 80%, 95%, and 100%.
7. Enforcement engine stops or pauses services safely.
8. SCPs are attached only after thresholds.

## Direct AWS calls vs proxy calls

Proxy Bedrock calls give near real-time budget control because the proxy counts tokens, reserves budget, calls Bedrock, parses actual usage, and refunds unused reserve.

Direct console/CLI Bedrock calls are detected through CloudTrail/EventBridge. They are estimated after the API call. For strict Bedrock cost control, route students through the proxy or LMS wrapper.

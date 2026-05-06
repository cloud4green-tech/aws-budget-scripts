# Bedrock Coverage

Covered by proxy:

- CountTokens
- Converse
- ConverseStream
- InvokeModel
- InvokeModelWithResponseStream

Covered by CloudTrail/EventBridge activity mapper:

- InvokeModel
- InvokeModelWithResponseStream
- Converse
- ConverseStream
- CountTokens
- CreateModelInvocationJob
- Agents runtime calls such as InvokeAgent and InvokeInlineAgent where CloudTrail data events are enabled
- Knowledge Base calls such as Retrieve and RetrieveAndGenerate where logged
- Flows and AgentCore activity where logged

Covered by pricing table model:

- model ID
- provider
- region
- input tokens
- output tokens
- cache read tokens
- cache write tokens
- batch pricing flag
- marketplace pricing flag
- provisioned throughput fields as custom rows

## Important FinOps note

CloudTrail does not always provide actual token usage for direct Bedrock calls. The proxy path is the authoritative path for real-time token-based budget control. The direct path uses safe estimates and threshold enforcement.

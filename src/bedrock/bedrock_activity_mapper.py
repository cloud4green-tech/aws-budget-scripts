from typing import Dict
from bedrock.bedrock_cost_calculator import calculate_token_cost_micros

BEDROCK_RUNTIME_EVENTS = {
    'InvokeModel', 'InvokeModelWithResponseStream', 'Converse', 'ConverseStream', 'CountTokens',
    'CreateModelInvocationJob', 'GetModelInvocationJob', 'ListModelInvocationJobs',
    'InvokeAgent', 'Retrieve', 'RetrieveAndGenerate', 'InvokeFlow', 'StartIngestionJob',
    'StartAsyncInvoke', 'GetAsyncInvoke', 'InvokeModelWithBidirectionalStream'
}

def map_bedrock_event(detail: Dict) -> Dict:
    event_name = detail.get('eventName', 'unknown')
    region = detail.get('awsRegion', 'unknown')
    req = detail.get('requestParameters', {}) or {}
    model_id = req.get('modelId') or req.get('foundationModelIdentifier') or req.get('inferenceProfileIdentifier') or req.get('modelIdentifier') or 'unknown'
    if event_name in ('InvokeModel', 'InvokeModelWithResponseStream', 'Converse', 'ConverseStream'):
        # Direct console/CLI CloudTrail does not expose actual tokens. Proxy provides exact reservation/refund.
        return {'resource_id': model_id, 'estimated_cost_micros': calculate_token_cost_micros(model_id, region, input_tokens=1000, output_tokens=1000), 'pricing_source': 'bedrock_cloudtrail_safe_estimate'}
    if event_name == 'CreateModelInvocationJob':
        return {'resource_id': model_id, 'estimated_cost_micros': calculate_token_cost_micros(model_id, region, input_tokens=10000, output_tokens=10000, mode='batch'), 'pricing_source': 'bedrock_batch_safe_estimate'}
    if event_name in ('InvokeAgent', 'RetrieveAndGenerate', 'Retrieve', 'InvokeFlow'):
        return {'resource_id': req.get('agentId') or req.get('knowledgeBaseId') or event_name, 'estimated_cost_micros': 10000, 'pricing_source': 'bedrock_agent_kb_estimate'}
    return {'resource_id': model_id, 'estimated_cost_micros': 0, 'pricing_source': 'bedrock_control_plane'}

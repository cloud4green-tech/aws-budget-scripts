import json
import logging
from typing import Dict
from utils import stable_hash
from budget_manager import get_user_by_account, record_usage_idempotent
from threshold_handler import evaluate_thresholds
from bedrock.bedrock_activity_mapper import map_bedrock_event

log = logging.getLogger(__name__)

ESTIMATED_EVENT_COST_MICROS = {
    'RunInstances': 5000,
    'StartInstances': 2000,
    'CreateTrainingJob': 50000,
    'CreateEndpoint': 100000,
    'StartNotebookInstance': 20000,
    'InvokeModel': 10000,
    'InvokeModelWithResponseStream': 10000,
    'Converse': 10000,
    'ConverseStream': 10000,
    'CreateModelInvocationJob': 50000,
    'StartJobRun': 50000,
    'RunTask': 10000,
    'CreateCluster': 50000,
}

def process_cloudtrail_event(detail: Dict) -> Dict:
    account_id = detail.get('recipientAccountId') or detail.get('userIdentity', {}).get('accountId') or detail.get('account')
    region = detail.get('awsRegion', 'unknown')
    event_name = detail.get('eventName', 'unknown')
    event_source = detail.get('eventSource', 'unknown')
    if not account_id:
        return {'ignored': 'missing account'}
    user = get_user_by_account(account_id)
    if not user:
        return {'ignored': f'no user for account {account_id}'}

    event_id = detail.get('eventID') or stable_hash(detail)
    cost = ESTIMATED_EVENT_COST_MICROS.get(event_name, 0)
    resource_id = event_name
    pricing_source = 'event_estimate'
    if 'bedrock' in event_source:
        mapped = map_bedrock_event(detail)
        cost = mapped.get('estimated_cost_micros', cost)
        resource_id = mapped.get('resource_id', event_name)
        pricing_source = mapped.get('pricing_source', 'bedrock_event_estimate')

    ok = record_usage_idempotent(
        user_id=user['user_id'],
        account_id=account_id,
        service=event_source.replace('.amazonaws.com', ''),
        region=region,
        event_id=event_id,
        event_name=event_name,
        resource_id=resource_id,
        cost_delta_micros=cost,
        pricing_source=pricing_source,
    )
    if ok:
        evaluate_thresholds(user['user_id'])
    return {'processed': ok, 'account_id': account_id, 'event_name': event_name, 'cost_micros': cost}

def lambda_handler(event, context):
    log.info('event ingest received')
    failures = []
    results = []
    for record in event.get('Records', []):
        try:
            body = json.loads(record['body'])
            detail = body.get('detail', body)
            results.append(process_cloudtrail_event(detail))
        except Exception:
            log.exception('failed record')
            failures.append({'itemIdentifier': record.get('messageId')})
    if 'Records' in event:
        return {'batchItemFailures': failures, 'results': results}
    detail = event.get('detail', event)
    return process_cloudtrail_event(detail)

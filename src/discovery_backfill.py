import json
import logging
import boto3
from typing import Dict, Iterable
from botocore.exceptions import ClientError

from config import ACTIVE_RESOURCES_TABLE, REGIONS, METER_WINDOW_SECONDS
from utils import now_epoch, stable_hash
from budget_manager import list_users, record_usage_idempotent
from cost_engine import meter_resource_cost_micros
from threshold_handler import evaluate_thresholds
from service_handlers import ec2_handler, sagemaker_handler, lambda_handler, ecs_handler, eks_handler, glue_handler, emr_handler

log = logging.getLogger(__name__)
ddb = boto3.client('dynamodb')
HANDLERS = [ec2_handler, sagemaker_handler, lambda_handler, ecs_handler, eks_handler, glue_handler, emr_handler]

def _n(v): return {'N': str(int(v))}
def _s(v): return {'S': str(v)}

def upsert_active_resource(resource: Dict):
    ts = now_epoch()
    metadata = resource.get('metadata', {})
    ddb.put_item(
        TableName=ACTIVE_RESOURCES_TABLE,
        Item={
            'resource_id': _s(resource['resource_id']),
            'account_id': _s(resource['account_id']),
            'owner': _s(resource.get('owner', resource['account_id'])),
            'service': _s(resource['service']),
            'region': _s(resource['region']),
            'start_time': _n(resource.get('start_time') or ts),
            'last_metered': _n(ts),
            'cost_rate_per_second_micros': _n(resource.get('cost_rate_per_second_micros', 0)),
            'status': _s(resource.get('status', 'running')),
            'priority': _n(resource.get('priority', 50)),
            'metadata': _s(json.dumps(metadata, default=str)[:4000]),
            'updated_at': _n(ts),
        },
    )

def get_previous(resource_id: str):
    resp = ddb.get_item(TableName=ACTIVE_RESOURCES_TABLE, Key={'resource_id': _s(resource_id)}, ConsistentRead=True)
    item = resp.get('Item')
    if not item:
        return None
    return {
        'resource_id': item['resource_id']['S'],
        'last_metered': int(item.get('last_metered', {'N': '0'})['N']),
        'cost_rate_per_second_micros': int(item.get('cost_rate_per_second_micros', {'N': '0'})['N']),
        'service': item.get('service', {}).get('S', ''),
        'region': item.get('region', {}).get('S', ''),
    }

def discover_account(user: Dict):
    account_id = user['account_id']
    total = 0
    for region in REGIONS:
        for handler in HANDLERS:
            try:
                resources = handler.discover(account_id, region)
            except Exception:
                log.exception('discover handler failed account=%s region=%s handler=%s', account_id, region, handler.__name__)
                continue
            for r in resources:
                prev = get_previous(r['resource_id'])
                now = now_epoch()
                elapsed = METER_WINDOW_SECONDS if not prev else max(0, min(METER_WINDOW_SECONDS * 3, now - prev['last_metered']))
                cost = meter_resource_cost_micros(r, elapsed)
                event_id = f"meter#{r['resource_id']}#{now // METER_WINDOW_SECONDS}"
                ok = record_usage_idempotent(
                    user_id=user['user_id'],
                    account_id=account_id,
                    service=r['service'],
                    region=region,
                    event_id=event_id,
                    event_name='DISCOVERY_METER',
                    resource_id=r['resource_id'],
                    cost_delta_micros=cost,
                    pricing_source='price_cache_or_fallback',
                )
                upsert_active_resource(r)
                if ok:
                    total += cost
    evaluate_thresholds(user['user_id'])
    return total

def lambda_handler(event, context):
    log.info('starting discovery/backfill event=%s', json.dumps(event, default=str)[:1000])
    totals = {}
    for user in list_users():
        totals[user['account_id']] = discover_account(user)
    return {'metered_accounts': len(totals), 'cost_micros_by_account': totals}

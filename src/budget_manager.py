import logging
import uuid
from decimal import Decimal
from typing import Dict, Optional, Tuple

import boto3
from botocore.exceptions import ClientError

from config import USERS_TABLE, USAGE_LOG_TABLE, EVENT_ID_TTL_SECONDS, DEFAULT_BUDGET_MICROS
from utils import now_epoch

log = logging.getLogger(__name__)
ddb = boto3.client('dynamodb')

def _n(v: int) -> Dict[str, str]:
    return {'N': str(int(v))}

def _s(v: str) -> Dict[str, str]:
    return {'S': str(v)}

def get_user(user_id: str) -> Optional[Dict]:
    resp = ddb.get_item(TableName=USERS_TABLE, Key={'user_id': _s(user_id)}, ConsistentRead=True)
    item = resp.get('Item')
    if not item:
        return None
    return {
        'user_id': item['user_id']['S'],
        'account_id': item['account_id']['S'],
        'email': item.get('email', {}).get('S', ''),
        'budget_total_micros': int(item.get('budget_total_micros', {'N': '0'})['N']),
        'budget_used_micros': int(item.get('budget_used_micros', {'N': '0'})['N']),
        'projected_used_micros': int(item.get('projected_used_micros', {'N': '0'})['N']),
        'reserved_micros': int(item.get('reserved_micros', {'N': '0'})['N']),
        'threshold_state': item.get('threshold_state', {}).get('S', 'OPEN'),
        'threshold_level': item.get('threshold_level', {}).get('S', '0'),
    }

def get_user_by_account(account_id: str) -> Optional[Dict]:
    resp = ddb.query(
        TableName=USERS_TABLE,
        IndexName='account_id-index',
        KeyConditionExpression='account_id = :a',
        ExpressionAttributeValues={':a': _s(account_id)},
        Limit=1,
        ConsistentRead=False,
    )
    items = resp.get('Items', [])
    return get_user(items[0]['user_id']['S']) if items else None

def init_or_reset_user(user_id: str, account_id: str, email: str = '', budget_total_micros: int = DEFAULT_BUDGET_MICROS):
    ts = now_epoch()
    ddb.put_item(
        TableName=USERS_TABLE,
        Item={
            'user_id': _s(user_id),
            'account_id': _s(account_id),
            'email': _s(email),
            'budget_total_micros': _n(budget_total_micros),
            'budget_used_micros': _n(0),
            'projected_used_micros': _n(0),
            'reserved_micros': _n(0),
            'threshold_state': _s('OPEN'),
            'threshold_level': _s('0'),
            'created_at': _n(ts),
            'updated_at': _n(ts),
        },
    )

def list_users(limit: int = 1000):
    paginator = ddb.get_paginator('scan')
    for page in paginator.paginate(TableName=USERS_TABLE, PaginationConfig={'PageSize': min(limit, 1000)}):
        for item in page.get('Items', []):
            yield {
                'user_id': item['user_id']['S'],
                'account_id': item['account_id']['S'],
                'email': item.get('email', {}).get('S', ''),
                'budget_total_micros': int(item.get('budget_total_micros', {'N': '0'})['N']),
                'budget_used_micros': int(item.get('budget_used_micros', {'N': '0'})['N']),
                'reserved_micros': int(item.get('reserved_micros', {'N': '0'})['N']),
                'threshold_state': item.get('threshold_state', {}).get('S', 'OPEN'),
                'threshold_level': item.get('threshold_level', {}).get('S', '0'),
            }

def available_micros(user_id: str) -> int:
    user = get_user(user_id)
    if not user:
        return 0
    return max(0, user['budget_total_micros'] - user['budget_used_micros'] - user['reserved_micros'])

def reserve_budget(user_id: str, amount_micros: int, reason: str) -> Tuple[bool, str]:
    if amount_micros <= 0:
        return True, ''
    reservation_id = f'reserve-{uuid.uuid4()}'
    ts = now_epoch()
    try:
        ddb.update_item(
            TableName=USERS_TABLE,
            Key={'user_id': _s(user_id)},
            UpdateExpression='ADD reserved_micros :r SET updated_at = :ts',
            ConditionExpression='attribute_exists(user_id) AND (budget_total_micros - budget_used_micros - reserved_micros) >= :r',
            ExpressionAttributeValues={':r': _n(amount_micros), ':ts': _n(ts)},
        )
        ddb.put_item(
            TableName=USAGE_LOG_TABLE,
            Item={
                'event_id': _s(reservation_id),
                'user_id': _s(user_id),
                'account_id': _s('proxy'),
                'service': _s('bedrock'),
                'region': _s('unknown'),
                'timestamp': _n(ts),
                'cost_delta_micros': _n(0),
                'reserved_micros': _n(amount_micros),
                'event_name': _s(f'RESERVE:{reason}'),
                'resource_id': _s(reason[:255]),
                'pricing_source': _s('reservation'),
                'ttl_epoch': _n(ts + EVENT_ID_TTL_SECONDS),
            },
            ConditionExpression='attribute_not_exists(event_id)',
        )
        return True, reservation_id
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return False, ''
        raise

def finalize_reservation(user_id: str, reservation_id: str, actual_micros: int, usage_item: Dict):
    actual_micros = max(0, int(actual_micros))
    reservation = ddb.get_item(TableName=USAGE_LOG_TABLE, Key={'event_id': _s(reservation_id)}, ConsistentRead=True).get('Item')
    reserved_micros = int(reservation.get('reserved_micros', {'N': '0'})['N']) if reservation else 0
    release_micros = reserved_micros
    ts = now_epoch()
    event_id = usage_item['event_id']
    try:
        ddb.transact_write_items(
            TransactItems=[
                {
                    'Update': {
                        'TableName': USERS_TABLE,
                        'Key': {'user_id': _s(user_id)},
                        'UpdateExpression': 'ADD budget_used_micros :used, reserved_micros :release SET projected_used_micros = budget_used_micros + :used, updated_at = :ts',
                        'ConditionExpression': 'attribute_exists(user_id)',
                        'ExpressionAttributeValues': {
                            ':used': _n(actual_micros),
                            ':release': _n(-release_micros),
                            ':ts': _n(ts),
                        },
                    }
                },
                {
                    'Put': {
                        'TableName': USAGE_LOG_TABLE,
                        'Item': _usage_ddb_item(usage_item, actual_micros, ts),
                        'ConditionExpression': 'attribute_not_exists(event_id)',
                    }
                },
            ]
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'TransactionCanceledException':
            log.warning('finalize reservation transaction canceled user=%s event=%s', user_id, event_id)
            return False
        raise
    return True

def refund_reservation(user_id: str, reservation_id: str):
    reservation = ddb.get_item(TableName=USAGE_LOG_TABLE, Key={'event_id': _s(reservation_id)}, ConsistentRead=True).get('Item')
    if not reservation:
        return
    reserved_micros = int(reservation.get('reserved_micros', {'N': '0'})['N'])
    if reserved_micros <= 0:
        return
    ddb.update_item(
        TableName=USERS_TABLE,
        Key={'user_id': _s(user_id)},
        UpdateExpression='ADD reserved_micros :r SET updated_at = :ts',
        ExpressionAttributeValues={':r': _n(-reserved_micros), ':ts': _n(now_epoch())},
    )

def record_usage_idempotent(user_id: str, account_id: str, service: str, region: str, event_id: str, event_name: str, resource_id: str, cost_delta_micros: int, pricing_source: str) -> bool:
    cost_delta_micros = max(0, int(cost_delta_micros))
    ts = now_epoch()
    item = _usage_ddb_item({
        'event_id': event_id,
        'user_id': user_id,
        'account_id': account_id,
        'service': service,
        'region': region,
        'event_name': event_name,
        'resource_id': resource_id,
        'pricing_source': pricing_source,
    }, cost_delta_micros, ts)
    try:
        ddb.transact_write_items(
            TransactItems=[
                {
                    'Put': {
                        'TableName': USAGE_LOG_TABLE,
                        'Item': item,
                        'ConditionExpression': 'attribute_not_exists(event_id)',
                    }
                },
                {
                    'Update': {
                        'TableName': USERS_TABLE,
                        'Key': {'user_id': _s(user_id)},
                        'UpdateExpression': 'ADD budget_used_micros :c SET projected_used_micros = budget_used_micros + :c, updated_at = :ts',
                        'ConditionExpression': 'attribute_exists(user_id)',
                        'ExpressionAttributeValues': {':c': _n(cost_delta_micros), ':ts': _n(ts)},
                    }
                },
            ]
        )
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'TransactionCanceledException':
            log.info('duplicate or missing user event ignored event_id=%s user=%s', event_id, user_id)
            return False
        raise

def update_threshold_state(user_id: str, threshold_state: str, threshold_level: str):
    ddb.update_item(
        TableName=USERS_TABLE,
        Key={'user_id': _s(user_id)},
        UpdateExpression='SET threshold_state = :s, threshold_level = :l, updated_at = :ts',
        ExpressionAttributeValues={':s': _s(threshold_state), ':l': _s(str(threshold_level)), ':ts': _n(now_epoch())},
    )

def _usage_ddb_item(usage_item: Dict, cost_delta_micros: int, ts: int) -> Dict:
    return {
        'event_id': _s(usage_item['event_id']),
        'user_id': _s(usage_item.get('user_id', 'unknown')),
        'account_id': _s(usage_item.get('account_id', 'unknown')),
        'service': _s(usage_item.get('service', 'unknown')),
        'region': _s(usage_item.get('region', 'unknown')),
        'timestamp': _n(ts),
        'cost_delta_micros': _n(cost_delta_micros),
        'event_name': _s(usage_item.get('event_name', 'unknown')),
        'resource_id': _s(usage_item.get('resource_id', 'unknown')[:1024]),
        'pricing_source': _s(usage_item.get('pricing_source', 'unknown')),
        'ttl_epoch': _n(ts + EVENT_ID_TTL_SECONDS),
    }

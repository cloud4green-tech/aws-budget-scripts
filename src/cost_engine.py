import logging
from decimal import Decimal
from typing import Dict, Optional
import boto3
from config import PRICE_CACHE_TABLE, SAFETY_FALLBACK_RATE_MICROS_PER_SECOND

log = logging.getLogger(__name__)
ddb = boto3.client('dynamodb')

DEFAULT_RATES_MICROS_PER_SECOND = {
    'ec2': 15,          # about $0.054/hr
    'rds': 25,          # about $0.09/hr
    'sagemaker': 60,    # conservative notebook/training fallback
    'ecs': 20,
    'eks': 30,
    'lambda': 1,
    'glue': 110,
    'emr': 150,
    'bedrock': 100,
}

def price_key(service: str, region: str, sku: str) -> str:
    return f'{service}#{region}#{sku}'

def get_price_record(key: str) -> Optional[Dict]:
    resp = ddb.get_item(TableName=PRICE_CACHE_TABLE, Key={'price_key': {'S': key}}, ConsistentRead=False)
    item = resp.get('Item')
    if not item:
        return None
    out = {k: next(iter(v.values())) for k, v in item.items()}
    for k in list(out.keys()):
        if k.endswith('_micros') or k.endswith('_per_second_micros') or k.endswith('_per_1k_micros') or k.endswith('_per_1m_micros'):
            out[k] = int(out[k])
    return out

def get_rate_per_second_micros(service: str, region: str, sku: str) -> int:
    rec = get_price_record(price_key(service, region, sku))
    if rec and rec.get('cost_rate_per_second_micros') is not None:
        return int(rec['cost_rate_per_second_micros'])
    return DEFAULT_RATES_MICROS_PER_SECOND.get(service, SAFETY_FALLBACK_RATE_MICROS_PER_SECOND)

def meter_resource_cost_micros(resource: Dict, elapsed_seconds: int) -> int:
    if elapsed_seconds <= 0:
        return 0
    rate = int(resource.get('cost_rate_per_second_micros') or get_rate_per_second_micros(resource['service'], resource['region'], resource.get('sku', resource.get('metadata', {}).get('instance_type', 'unknown'))))
    return max(0, rate * elapsed_seconds)

def lambda_request_estimate_micros(duration_ms: int, memory_mb: int, requests: int = 1) -> int:
    gb_seconds = Decimal(duration_ms) / Decimal(1000) * Decimal(memory_mb) / Decimal(1024)
    compute = gb_seconds * Decimal('0.0000166667') * Decimal(1000000)
    request_cost = Decimal(requests) * Decimal('0.20') # micros = $0.20 per 1M requests
    return int(compute + request_cost)

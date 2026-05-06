import json
import logging
import time
from decimal import Decimal
from typing import Dict, List
import boto3
from botocore.exceptions import ClientError
from config import PRICE_CACHE_TABLE, REGIONS

log = logging.getLogger(__name__)
ddb = boto3.client('dynamodb')
pricing = boto3.client('pricing', region_name='us-east-1')

REGION_LOCATION = {
    'us-east-1': 'US East (N. Virginia)',
    'us-east-2': 'US East (Ohio)',
    'us-west-2': 'US West (Oregon)',
    'ap-south-1': 'Asia Pacific (Mumbai)',
}

FALLBACK_RATES = [
    ('ec2', 't3.micro', 3), ('ec2', 't3.small', 6), ('ec2', 't3.medium', 12), ('ec2', 't3.large', 24),
    ('rds', 'db.t3.micro', 5), ('sagemaker', 'ml.t3.medium', 14), ('sagemaker', 'training', 60), ('sagemaker', 'endpoint', 60),
    ('ecs', 'task', 20), ('eks', 'cluster', 28), ('glue', 'job', 110), ('emr', 'cluster', 150), ('lambda', 'python3.12', 1),
]

BEDROCK_SEED = [
    {'model_id': 'amazon.nova-micro-v1:0', 'provider': 'Amazon', 'input_per_1k_micros': 35, 'output_per_1k_micros': 140},
    {'model_id': 'amazon.nova-lite-v1:0', 'provider': 'Amazon', 'input_per_1k_micros': 60, 'output_per_1k_micros': 240},
    {'model_id': 'amazon.nova-pro-v1:0', 'provider': 'Amazon', 'input_per_1k_micros': 800, 'output_per_1k_micros': 3200},
    {'model_id': 'anthropic.claude-3-haiku-20240307-v1:0', 'provider': 'Anthropic', 'input_per_1k_micros': 250, 'output_per_1k_micros': 1250},
    {'model_id': 'anthropic.claude-3-5-sonnet-20240620-v1:0', 'provider': 'Anthropic', 'input_per_1k_micros': 3000, 'output_per_1k_micros': 15000},
    {'model_id': 'meta.llama3-8b-instruct-v1:0', 'provider': 'Meta', 'input_per_1k_micros': 400, 'output_per_1k_micros': 600},
]

def put_price(item: Dict):
    ddb.put_item(TableName=PRICE_CACHE_TABLE, Item={k: _to_attr(v) for k, v in item.items()})

def _to_attr(v):
    if isinstance(v, bool):
        return {'BOOL': v}
    if isinstance(v, int):
        return {'N': str(v)}
    if isinstance(v, Decimal):
        return {'N': str(v)}
    return {'S': str(v)}

def _extract_usd_hourly(price_item: Dict) -> Decimal:
    terms = price_item.get('terms', {}).get('OnDemand', {})
    for term in terms.values():
        for dim in term.get('priceDimensions', {}).values():
            usd = dim.get('pricePerUnit', {}).get('USD')
            unit = dim.get('unit', '')
            if usd is not None and ('Hrs' in unit or 'Hour' in unit):
                return Decimal(usd)
    return Decimal('0')

def refresh_ec2(region: str, instance_types: List[str]):
    location = REGION_LOCATION.get(region)
    if not location:
        return 0
    loaded = 0
    for itype in instance_types:
        try:
            resp = pricing.get_products(
                ServiceCode='AmazonEC2',
                Filters=[
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location},
                    {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': itype},
                    {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'},
                    {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                    {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
                    {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'},
                ],
                MaxResults=1,
            )
            if not resp.get('PriceList'):
                continue
            item = json.loads(resp['PriceList'][0])
            hourly = _extract_usd_hourly(item)
            micros_per_second = int(hourly * Decimal(1000000) / Decimal(3600))
            put_price({'price_key': f'ec2#{region}#{itype}', 'service': 'ec2', 'region': region, 'instance_type': itype, 'cost_rate_per_second_micros': micros_per_second, 'pricing_source': 'aws_pricing_api', 'ttl': int(time.time()) + 86400, 'updated_at': int(time.time())})
            loaded += 1
        except Exception:
            log.exception('EC2 price refresh failed region=%s type=%s', region, itype)
    return loaded

def seed_fallbacks():
    loaded = 0
    for region in REGIONS:
        for service, sku, rate in FALLBACK_RATES:
            put_price({'price_key': f'{service}#{region}#{sku}', 'service': service, 'region': region, 'instance_type': sku, 'cost_rate_per_second_micros': rate, 'pricing_source': 'safe_fallback_seed', 'ttl': int(time.time()) + 7 * 86400, 'updated_at': int(time.time())})
            loaded += 1
    for region in REGIONS + ['global']:
        for p in BEDROCK_SEED:
            put_price({'price_key': f'bedrock#{region}#{p["model_id"]}', 'service': 'bedrock', 'region': region, 'model_id': p['model_id'], 'provider': p['provider'], 'input_per_1k_micros': p['input_per_1k_micros'], 'output_per_1k_micros': p['output_per_1k_micros'], 'cache_read_per_1k_micros': max(1, int(p['input_per_1k_micros'] * 0.1)), 'cache_write_per_1k_micros': p['input_per_1k_micros'], 'marketplace_pricing_flag': 'false', 'pricing_source': 'seed_table_update_with_aws_bedrock_pricing', 'ttl': int(time.time()) + 7 * 86400, 'updated_at': int(time.time())})
            loaded += 1
    return loaded

def lambda_handler(event, context):
    loaded = seed_fallbacks()
    ec2_loaded = 0
    for region in REGIONS:
        ec2_loaded += refresh_ec2(region, ['t3.micro', 't3.small', 't3.medium', 't3.large'])
    return {'fallback_loaded': loaded, 'ec2_aws_pricing_loaded': ec2_loaded, 'regions': REGIONS}

from decimal import Decimal
from typing import Dict
import boto3
from config import PRICE_CACHE_TABLE

_ddb = boto3.client('dynamodb')

DEFAULT_BEDROCK_PRICES = {
    # micros per 1K tokens. Safe training defaults. Update with loader for production accuracy.
    'anthropic.claude-3-haiku-20240307-v1:0': {'input_per_1k_micros': 250, 'output_per_1k_micros': 1250},
    'anthropic.claude-3-5-sonnet-20240620-v1:0': {'input_per_1k_micros': 3000, 'output_per_1k_micros': 15000},
    'amazon.nova-micro-v1:0': {'input_per_1k_micros': 35, 'output_per_1k_micros': 140},
    'amazon.nova-lite-v1:0': {'input_per_1k_micros': 60, 'output_per_1k_micros': 240},
    'amazon.nova-pro-v1:0': {'input_per_1k_micros': 800, 'output_per_1k_micros': 3200},
    'meta.llama3-8b-instruct-v1:0': {'input_per_1k_micros': 400, 'output_per_1k_micros': 600},
}

def _get_price(model_id: str, region: str) -> Dict:
    keys = [f'bedrock#{region}#{model_id}', f'bedrock#global#{model_id}']
    for key in keys:
        resp = _ddb.get_item(TableName=PRICE_CACHE_TABLE, Key={'price_key': {'S': key}})
        item = resp.get('Item')
        if item:
            return {k: next(iter(v.values())) for k, v in item.items()}
    return DEFAULT_BEDROCK_PRICES.get(model_id, {'input_per_1k_micros': 3000, 'output_per_1k_micros': 15000, 'pricing_source': 'safe_fallback'})

def calculate_token_cost_micros(model_id: str, region: str, input_tokens: int = 0, output_tokens: int = 0, cache_read_tokens: int = 0, cache_write_tokens: int = 0, mode: str = 'ondemand') -> int:
    p = _get_price(model_id, region)
    def _v(name, fallback=0):
        val = p.get(name, fallback)
        return int(val) if str(val).isdigit() else int(Decimal(str(val)))
    input_price = _v('input_per_1k_micros', _v('input_per_1m_micros', 0) / 1000)
    output_price = _v('output_per_1k_micros', _v('output_per_1m_micros', 0) / 1000)
    cache_read_price = _v('cache_read_per_1k_micros', max(1, input_price // 10))
    cache_write_price = _v('cache_write_per_1k_micros', input_price)
    cost = Decimal(input_tokens) * Decimal(input_price) / Decimal(1000)
    cost += Decimal(output_tokens) * Decimal(output_price) / Decimal(1000)
    cost += Decimal(cache_read_tokens) * Decimal(cache_read_price) / Decimal(1000)
    cost += Decimal(cache_write_tokens) * Decimal(cache_write_price) / Decimal(1000)
    if mode == 'batch':
        cost *= Decimal('0.5')
    return int(cost)

def reserve_amount_for_request(model_id: str, region: str, input_tokens: int, max_output_tokens: int, cache_read_tokens: int = 0, cache_write_tokens: int = 0) -> int:
    return calculate_token_cost_micros(
        model_id=model_id,
        region=region,
        input_tokens=input_tokens,
        output_tokens=max_output_tokens,
        cache_read_tokens=cache_read_tokens,
        cache_write_tokens=cache_write_tokens,
    )

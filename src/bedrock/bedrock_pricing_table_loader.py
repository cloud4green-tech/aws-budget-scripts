import csv
import io
import time
import boto3
from config import PRICE_CACHE_TABLE

# Loader accepts CSV exported from AWS pricing workbooks or a manually maintained FinOps price sheet.
# Required columns: model_id,region,input_per_1k_micros,output_per_1k_micros
# Optional: cache_read_per_1k_micros,cache_write_per_1k_micros,provider,marketplace_pricing_flag,pricing_source

ddb = boto3.client('dynamodb')

def load_csv_text(csv_text: str):
    loaded = 0
    for row in csv.DictReader(io.StringIO(csv_text)):
        model_id = row['model_id'].strip()
        region = row.get('region', 'global').strip() or 'global'
        key = f'bedrock#{region}#{model_id}'
        item = {
            'price_key': {'S': key},
            'service': {'S': 'bedrock'},
            'region': {'S': region},
            'model_id': {'S': model_id},
            'provider': {'S': row.get('provider', 'unknown')},
            'input_per_1k_micros': {'N': str(int(float(row.get('input_per_1k_micros', 0))))},
            'output_per_1k_micros': {'N': str(int(float(row.get('output_per_1k_micros', 0))))},
            'cache_read_per_1k_micros': {'N': str(int(float(row.get('cache_read_per_1k_micros', 0))))},
            'cache_write_per_1k_micros': {'N': str(int(float(row.get('cache_write_per_1k_micros', 0))))},
            'marketplace_pricing_flag': {'S': row.get('marketplace_pricing_flag', 'false')},
            'pricing_source': {'S': row.get('pricing_source', 'manual_finops_table')},
            'updated_at': {'N': str(int(time.time()))},
            'ttl': {'N': str(int(time.time()) + 30 * 24 * 3600)},
        }
        ddb.put_item(TableName=PRICE_CACHE_TABLE, Item=item)
        loaded += 1
    return {'loaded': loaded}

def lambda_handler(event, context):
    if 'csv_text' in event:
        return load_csv_text(event['csv_text'])
    return {'message': 'pass csv_text to load Bedrock pricing rows'}

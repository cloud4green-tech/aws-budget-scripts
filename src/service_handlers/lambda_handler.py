from aws_clients import assumed_client
from cost_engine import get_rate_per_second_micros
from utils import now_epoch


def discover(account_id: str, region: str):
    lam = assumed_client(account_id, 'lambda', region)
    resources = []
    paginator = lam.get_paginator('list_functions')
    for page in paginator.paginate():
        for fn in page.get('Functions', []):
            arn = fn['FunctionArn']
            resources.append({'resource_id': arn, 'account_id': account_id, 'owner': account_id, 'service': 'lambda', 'region': region, 'start_time': now_epoch(), 'status': 'configured', 'priority': 30, 'cost_rate_per_second_micros': get_rate_per_second_micros('lambda', region, fn.get('Runtime', 'unknown')), 'metadata': {'function_name': fn['FunctionName'], 'runtime': fn.get('Runtime'), 'memory': fn.get('MemorySize')}})
    return resources


def stop_or_pause(account_id: str, region: str, hard: bool = False):
    lam = assumed_client(account_id, 'lambda', region)
    actions = []
    for r in discover(account_id, region):
        name = r['metadata']['function_name']
        try:
            lam.put_function_concurrency(FunctionName=name, ReservedConcurrentExecutions=0)
            actions.append({'service': 'lambda', 'region': region, 'throttled': name})
        except Exception as e:
            actions.append({'service': 'lambda', 'region': region, 'function': name, 'error': str(e)})
    try:
        paginator = lam.get_paginator('list_event_source_mappings')
        for page in paginator.paginate():
            for mapping in page.get('EventSourceMappings', []):
                if mapping.get('State') != 'Disabled':
                    lam.update_event_source_mapping(UUID=mapping['UUID'], Enabled=False)
                    actions.append({'service': 'lambda', 'region': region, 'disabled_event_source': mapping['UUID']})
    except Exception as e:
        actions.append({'service': 'lambda', 'region': region, 'error': f'event source disable failed: {e}'})
    return actions

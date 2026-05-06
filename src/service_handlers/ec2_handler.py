import logging
from aws_clients import assumed_client
from cost_engine import get_rate_per_second_micros

log = logging.getLogger(__name__)

def discover(account_id: str, region: str):
    ec2 = assumed_client(account_id, 'ec2', region)
    resources = []
    paginator = ec2.get_paginator('describe_instances')
    for page in paginator.paginate(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]):
        for res in page.get('Reservations', []):
            for i in res.get('Instances', []):
                instance_type = i.get('InstanceType', 'unknown')
                launch = i.get('LaunchTime')
                resources.append({
                    'resource_id': i['InstanceId'],
                    'account_id': account_id,
                    'owner': account_id,
                    'service': 'ec2',
                    'region': region,
                    'start_time': int(launch.timestamp()) if launch else 0,
                    'status': 'running',
                    'priority': 50,
                    'cost_rate_per_second_micros': get_rate_per_second_micros('ec2', region, instance_type),
                    'metadata': {'instance_type': instance_type, 'state': i.get('State', {}).get('Name')},
                })
    return resources

def stop_or_pause(account_id: str, region: str, hard: bool = False):
    ec2 = assumed_client(account_id, 'ec2', region)
    ids = [r['resource_id'] for r in discover(account_id, region)]
    if not ids:
        return []
    # stop only. Never terminate.
    ec2.stop_instances(InstanceIds=ids)
    return [{'service': 'ec2', 'region': region, 'stopped': ids}]

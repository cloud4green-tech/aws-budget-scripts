from aws_clients import assumed_client
from cost_engine import get_rate_per_second_micros
from utils import now_epoch


def discover(account_id: str, region: str):
    ecs = assumed_client(account_id, 'ecs', region)
    resources = []
    for cluster_arn in ecs.list_clusters().get('clusterArns', []):
        services = ecs.list_services(cluster=cluster_arn).get('serviceArns', [])
        if services:
            desc = ecs.describe_services(cluster=cluster_arn, services=services).get('services', [])
            for s in desc:
                if s.get('desiredCount', 0) > 0 or s.get('runningCount', 0) > 0:
                    resources.append({'resource_id': s['serviceArn'], 'account_id': account_id, 'owner': account_id, 'service': 'ecs', 'region': region, 'start_time': now_epoch(), 'status': 'running', 'priority': 60, 'cost_rate_per_second_micros': get_rate_per_second_micros('ecs', region, 'service'), 'metadata': {'cluster': cluster_arn, 'serviceName': s['serviceName'], 'desired': s.get('desiredCount'), 'running': s.get('runningCount')}})
        tasks = ecs.list_tasks(cluster=cluster_arn, desiredStatus='RUNNING').get('taskArns', [])
        for t in tasks:
            resources.append({'resource_id': t, 'account_id': account_id, 'owner': account_id, 'service': 'ecs', 'region': region, 'start_time': now_epoch(), 'status': 'running', 'priority': 60, 'cost_rate_per_second_micros': get_rate_per_second_micros('ecs', region, 'task'), 'metadata': {'cluster': cluster_arn}})
    return resources


def stop_or_pause(account_id: str, region: str, hard: bool = False):
    ecs = assumed_client(account_id, 'ecs', region)
    actions = []
    for cluster_arn in ecs.list_clusters().get('clusterArns', []):
        for service_arn in ecs.list_services(cluster=cluster_arn).get('serviceArns', []):
            try:
                ecs.update_service(cluster=cluster_arn, service=service_arn, desiredCount=0)
                actions.append({'service': 'ecs', 'region': region, 'scaled_service_to_zero': service_arn})
            except Exception as e:
                actions.append({'service': 'ecs', 'region': region, 'service': service_arn, 'error': str(e)})
        for task_arn in ecs.list_tasks(cluster=cluster_arn, desiredStatus='RUNNING').get('taskArns', []):
            try:
                ecs.stop_task(cluster=cluster_arn, task=task_arn, reason='Cloud4Green budget threshold reached')
                actions.append({'service': 'ecs', 'region': region, 'stopped_task': task_arn})
            except Exception as e:
                actions.append({'service': 'ecs', 'region': region, 'task': task_arn, 'error': str(e)})
    return actions

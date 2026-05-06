from aws_clients import assumed_client
from cost_engine import get_rate_per_second_micros
from utils import now_epoch


def discover(account_id: str, region: str):
    eks = assumed_client(account_id, 'eks', region)
    resources = []
    for name in eks.list_clusters().get('clusters', []):
        desc = eks.describe_cluster(name=name)['cluster']
        resources.append({'resource_id': desc['arn'], 'account_id': account_id, 'owner': account_id, 'service': 'eks', 'region': region, 'start_time': int(desc.get('createdAt').timestamp()) if desc.get('createdAt') else now_epoch(), 'status': desc.get('status'), 'priority': 65, 'cost_rate_per_second_micros': get_rate_per_second_micros('eks', region, 'cluster'), 'metadata': {'cluster': name}})
    return resources


def stop_or_pause(account_id: str, region: str, hard: bool = False):
    eks = assumed_client(account_id, 'eks', region)
    actions = []
    for cluster in eks.list_clusters().get('clusters', []):
        for ng in eks.list_nodegroups(clusterName=cluster).get('nodegroups', []):
            try:
                eks.update_nodegroup_config(clusterName=cluster, nodegroupName=ng, scalingConfig={'minSize': 0, 'desiredSize': 0})
                actions.append({'service': 'eks', 'region': region, 'scaled_nodegroup_to_zero': f'{cluster}/{ng}'})
            except Exception as e:
                actions.append({'service': 'eks', 'region': region, 'nodegroup': f'{cluster}/{ng}', 'error': str(e)})
    return actions

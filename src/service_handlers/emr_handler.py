from aws_clients import assumed_client
from cost_engine import get_rate_per_second_micros
from utils import now_epoch


def discover(account_id: str, region: str):
    emr = assumed_client(account_id, 'emr', region)
    resources = []
    clusters = emr.list_clusters(ClusterStates=['STARTING','BOOTSTRAPPING','RUNNING','WAITING']).get('Clusters', [])
    for c in clusters:
        resources.append({'resource_id': c['Id'], 'account_id': account_id, 'owner': account_id, 'service': 'emr', 'region': region, 'start_time': int(c['Status']['Timeline']['CreationDateTime'].timestamp()) if c.get('Status', {}).get('Timeline', {}).get('CreationDateTime') else now_epoch(), 'status': c['Status']['State'], 'priority': 85, 'cost_rate_per_second_micros': get_rate_per_second_micros('emr', region, 'cluster'), 'metadata': {'name': c.get('Name')}})
    return resources

def stop_or_pause(account_id: str, region: str, hard: bool = False):
    # Classic EMR clusters do not have a safe stop/pause. Terminate is not allowed by Cloud4Green rule.
    actions = []
    for r in discover(account_id, region):
        actions.append({'service': 'emr', 'region': region, 'resource': r['resource_id'], 'note': 'classic EMR cannot be safely stopped; new starts are blocked by SCP and admin alert is sent'})
    try:
        emr_serverless = assumed_client(account_id, 'emr-serverless', region)
        for app in emr_serverless.list_applications(states=['STARTED']).get('applications', []):
            emr_serverless.stop_application(applicationId=app['id'])
            actions.append({'service': 'emr-serverless', 'region': region, 'stopped_application': app['id']})
    except Exception as e:
        actions.append({'service': 'emr-serverless', 'region': region, 'error': str(e)})
    return actions

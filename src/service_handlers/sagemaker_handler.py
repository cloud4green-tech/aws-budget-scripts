import logging
from aws_clients import assumed_client
from cost_engine import get_rate_per_second_micros
from config import ALLOW_SAGEMAKER_ENDPOINT_DELETE
from utils import now_epoch

log = logging.getLogger(__name__)

def discover(account_id: str, region: str):
    sm = assumed_client(account_id, 'sagemaker', region)
    resources = []
    try:
        for nb in sm.list_notebook_instances(StatusEquals='InService').get('NotebookInstances', []):
            name = nb['NotebookInstanceName']
            itype = nb.get('InstanceType', 'ml.unknown')
            resources.append({'resource_id': name, 'account_id': account_id, 'owner': account_id, 'service': 'sagemaker', 'region': region, 'start_time': now_epoch(), 'status': 'running', 'priority': 70, 'cost_rate_per_second_micros': get_rate_per_second_micros('sagemaker', region, itype), 'metadata': {'type': 'notebook', 'instance_type': itype}})
    except Exception as e:
        log.warning('notebook discover failed %s', e)
    try:
        for job in sm.list_training_jobs(StatusEquals='InProgress').get('TrainingJobSummaries', []):
            name = job['TrainingJobName']
            desc = sm.describe_training_job(TrainingJobName=name)
            algo = desc.get('AlgorithmSpecification', {}).get('TrainingImage', 'unknown')
            resources.append({'resource_id': name, 'account_id': account_id, 'owner': account_id, 'service': 'sagemaker', 'region': region, 'start_time': int(desc.get('CreationTime').timestamp()) if desc.get('CreationTime') else now_epoch(), 'status': 'running', 'priority': 80, 'cost_rate_per_second_micros': get_rate_per_second_micros('sagemaker', region, 'training'), 'metadata': {'type': 'training', 'image': algo}})
    except Exception as e:
        log.warning('training discover failed %s', e)
    try:
        for ep in sm.list_endpoints(StatusEquals='InService').get('Endpoints', []):
            name = ep['EndpointName']
            resources.append({'resource_id': name, 'account_id': account_id, 'owner': account_id, 'service': 'sagemaker', 'region': region, 'start_time': int(ep.get('CreationTime').timestamp()) if ep.get('CreationTime') else now_epoch(), 'status': 'running', 'priority': 95, 'cost_rate_per_second_micros': get_rate_per_second_micros('sagemaker', region, 'endpoint'), 'metadata': {'type': 'endpoint', 'note': 'cannot stop safely; blocked by SCP'}})
    except Exception as e:
        log.warning('endpoint discover failed %s', e)
    return resources

def stop_or_pause(account_id: str, region: str, hard: bool = False):
    sm = assumed_client(account_id, 'sagemaker', region)
    actions = []
    try:
        for nb in sm.list_notebook_instances(StatusEquals='InService').get('NotebookInstances', []):
            sm.stop_notebook_instance(NotebookInstanceName=nb['NotebookInstanceName'])
            actions.append({'service': 'sagemaker', 'region': region, 'stopped_notebook': nb['NotebookInstanceName']})
    except Exception as e:
        actions.append({'service': 'sagemaker', 'region': region, 'error': f'notebook stop failed: {e}'})
    try:
        for job in sm.list_training_jobs(StatusEquals='InProgress').get('TrainingJobSummaries', []):
            sm.stop_training_job(TrainingJobName=job['TrainingJobName'])
            actions.append({'service': 'sagemaker', 'region': region, 'stopped_training': job['TrainingJobName']})
    except Exception as e:
        actions.append({'service': 'sagemaker', 'region': region, 'error': f'training stop failed: {e}'})
    # Never delete endpoints by default.
    if ALLOW_SAGEMAKER_ENDPOINT_DELETE:
        actions.append({'service': 'sagemaker', 'region': region, 'note': 'endpoint delete allowed but not implemented in safe release'})
    else:
        actions.append({'service': 'sagemaker', 'region': region, 'note': 'endpoints are not deleted; invocation is blocked by SCP/proxy'})
    return actions

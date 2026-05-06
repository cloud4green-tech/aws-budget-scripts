from aws_clients import assumed_client
from cost_engine import get_rate_per_second_micros
from utils import now_epoch

RUNNING = {'STARTING', 'RUNNING', 'STOPPING'}

def discover(account_id: str, region: str):
    glue = assumed_client(account_id, 'glue', region)
    resources = []
    for job_name in glue.get_jobs().get('Jobs', []):
        name = job_name['Name']
        runs = glue.get_job_runs(JobName=name, MaxResults=10).get('JobRuns', [])
        for run in runs:
            if run.get('JobRunState') in RUNNING:
                resources.append({'resource_id': f'{name}/{run["Id"]}', 'account_id': account_id, 'owner': account_id, 'service': 'glue', 'region': region, 'start_time': int(run.get('StartedOn').timestamp()) if run.get('StartedOn') else now_epoch(), 'status': run.get('JobRunState'), 'priority': 75, 'cost_rate_per_second_micros': get_rate_per_second_micros('glue', region, 'job'), 'metadata': {'job': name, 'run_id': run['Id']}})
    return resources

def stop_or_pause(account_id: str, region: str, hard: bool = False):
    glue = assumed_client(account_id, 'glue', region)
    actions = []
    for r in discover(account_id, region):
        try:
            glue.batch_stop_job_run(JobName=r['metadata']['job'], JobRunIds=[r['metadata']['run_id']])
            actions.append({'service': 'glue', 'region': region, 'stopped_job_run': r['resource_id']})
        except Exception as e:
            actions.append({'service': 'glue', 'region': region, 'resource': r['resource_id'], 'error': str(e)})
    return actions

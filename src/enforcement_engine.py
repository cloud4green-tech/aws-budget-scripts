import logging
import boto3
from botocore.exceptions import ClientError
from config import REGIONS, PRESTOP_SCP_ID, HARDLOCK_SCP_ID, MANAGEMENT_REGION
from sns_notifier import notify_once
from service_handlers import ec2_handler, sagemaker_handler, lambda_handler, ecs_handler, eks_handler, glue_handler, emr_handler, bedrock_handler

log = logging.getLogger(__name__)
org = boto3.client('organizations', region_name=MANAGEMENT_REGION)

SAFE_STOP_HANDLERS = [
    ec2_handler,
    sagemaker_handler,
    lambda_handler,
    ecs_handler,
    eks_handler,
    glue_handler,
    emr_handler,
    bedrock_handler,
]

def _attach_scp(policy_id: str, account_id: str):
    if not policy_id:
        log.warning('SCP policy ID not configured')
        return
    try:
        org.attach_policy(PolicyId=policy_id, TargetId=account_id)
        log.info('attached SCP %s to account %s', policy_id, account_id)
    except ClientError as e:
        code = e.response['Error']['Code']
        if code in ('DuplicatePolicyAttachmentException', 'PolicyAlreadyAttachedException'):
            return
        if code == 'PolicyNotFoundException':
            log.error('SCP policy not found: %s', policy_id)
            return
        raise

def _detach_scp(policy_id: str, account_id: str):
    if not policy_id:
        return
    try:
        org.detach_policy(PolicyId=policy_id, TargetId=account_id)
    except ClientError as e:
        if e.response['Error']['Code'] in ('PolicyNotAttachedException', 'PolicyNotFoundException'):
            return
        raise

def stop_or_pause_high_cost(user: dict, hard: bool = False):
    account_id = user['account_id']
    summary = []
    for region in REGIONS:
        for handler in SAFE_STOP_HANDLERS:
            try:
                result = handler.stop_or_pause(account_id=account_id, region=region, hard=hard)
                if result:
                    summary.extend(result if isinstance(result, list) else [result])
            except Exception as e:
                log.exception('handler failed account=%s region=%s handler=%s', account_id, region, handler.__name__)
                summary.append({'handler': handler.__name__, 'region': region, 'error': str(e)})
    return summary

def apply_pre_stop(user: dict):
    log.warning('applying pre-stop for account=%s', user['account_id'])
    summary = stop_or_pause_high_cost(user, hard=False)
    _attach_scp(PRESTOP_SCP_ID, user['account_id'])
    notify_once(user, '95', user.get('budget_used_micros', 0), user.get('budget_total_micros', 0), extra=f'Pre-stop actions: {summary[:10]}')
    return summary

def apply_hard_lock(user: dict):
    log.warning('applying hard-lock for account=%s', user['account_id'])
    summary = stop_or_pause_high_cost(user, hard=True)
    _attach_scp(HARDLOCK_SCP_ID, user['account_id'])
    notify_once(user, '100', user.get('budget_used_micros', 0), user.get('budget_total_micros', 0), extra=f'Hard-lock stop actions: {summary[:10]}')
    return summary

def reset_account(user: dict):
    account_id = user['account_id']
    _detach_scp(PRESTOP_SCP_ID, account_id)
    _detach_scp(HARDLOCK_SCP_ID, account_id)

import boto3
from functools import lru_cache
from typing import Dict, Optional
from config import MEMBER_ROLE_NAME, EXTERNAL_ID, MANAGEMENT_REGION

@lru_cache(maxsize=128)
def client(service: str, region: Optional[str] = None):
    return boto3.client(service, region_name=region or MANAGEMENT_REGION)

@lru_cache(maxsize=128)
def resource(service: str, region: Optional[str] = None):
    return boto3.resource(service, region_name=region or MANAGEMENT_REGION)

@lru_cache(maxsize=512)
def assumed_session(account_id: str, region: str = MANAGEMENT_REGION):
    sts = boto3.client('sts', region_name=MANAGEMENT_REGION)
    role_arn = f'arn:aws:iam::{account_id}:role/{MEMBER_ROLE_NAME}'
    kwargs = {
        'RoleArn': role_arn,
        'RoleSessionName': 'c4g-budget-enforcer'
    }
    if EXTERNAL_ID:
        kwargs['ExternalId'] = EXTERNAL_ID
    resp = sts.assume_role(**kwargs)
    c = resp['Credentials']
    return boto3.Session(
        aws_access_key_id=c['AccessKeyId'],
        aws_secret_access_key=c['SecretAccessKey'],
        aws_session_token=c['SessionToken'],
        region_name=region,
    )

def assumed_client(account_id: str, service: str, region: str):
    return assumed_session(account_id, region).client(service, region_name=region)

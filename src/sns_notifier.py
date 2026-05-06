import logging
import boto3
from botocore.exceptions import ClientError
from config import SNS_TOPIC_ARN, NOTIFICATION_LOCKS_TABLE, NOTIFICATION_TTL_SECONDS, SUPPORT_EMAIL
from utils import now_epoch, dollars

log = logging.getLogger(__name__)
sns = boto3.client('sns')
ddb = boto3.client('dynamodb')

MESSAGES = {
    '80': 'You have used 80% of your assigned budget. Please monitor your usage to avoid service interruption.',
    '95': 'Your services are going to stop because you are about to hit your assigned budget.',
    '100': f'You have hit your assigned budget. Contact support team {SUPPORT_EMAIL} or your administrator',
}

def notify_once(user: dict, threshold: str, used_micros: int, total_micros: int, extra: str = ''):
    if not SNS_TOPIC_ARN:
        log.warning('SNS_TOPIC_ARN not configured, notification skipped')
        return False
    lock_id = f"{user['user_id']}#{threshold}"
    ts = now_epoch()
    try:
        ddb.put_item(
            TableName=NOTIFICATION_LOCKS_TABLE,
            Item={
                'lock_id': {'S': lock_id},
                'user_id': {'S': user['user_id']},
                'threshold': {'S': str(threshold)},
                'sent_at': {'N': str(ts)},
                'ttl': {'N': str(ts + NOTIFICATION_TTL_SECONDS)},
            },
            ConditionExpression='attribute_not_exists(lock_id)',
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return False
        raise
    message = MESSAGES[str(threshold)]
    subject = f"Cloud4Green AWS lab budget {threshold}% alert - {user.get('account_id')}"
    body = (
        f"{message}\n\n"
        f"Student/User: {user.get('user_id')}\n"
        f"AWS account: {user.get('account_id')}\n"
        f"Budget used: ${dollars(used_micros):.6f} of ${dollars(total_micros):.2f}\n"
        f"Threshold: {threshold}%\n"
        f"{extra}\n"
    )
    sns.publish(TopicArn=SNS_TOPIC_ARN, Subject=subject[:100], Message=body)
    return True

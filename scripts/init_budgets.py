import argparse
import time
import boto3

parser = argparse.ArgumentParser()
parser.add_argument('--table', required=True)
parser.add_argument('--accounts', required=True, help='comma separated account ids')
parser.add_argument('--budget-usd', type=float, default=2.0)
parser.add_argument('--email-domain', default='cloud4green.com')
args = parser.parse_args()

ddb = boto3.client('dynamodb')
budget_micros = int(args.budget_usd * 1_000_000)
now = int(time.time())
for account_id in [a.strip() for a in args.accounts.split(',') if a.strip()]:
    user_id = f'student-{account_id}'
    email = f'{user_id}@{args.email_domain}'
    ddb.put_item(
        TableName=args.table,
        Item={
            'user_id': {'S': user_id},
            'account_id': {'S': account_id},
            'email': {'S': email},
            'budget_total_micros': {'N': str(budget_micros)},
            'budget_used_micros': {'N': '0'},
            'projected_used_micros': {'N': '0'},
            'reserved_micros': {'N': '0'},
            'threshold_state': {'S': 'OPEN'},
            'threshold_level': {'S': '0'},
            'created_at': {'N': str(now)},
            'updated_at': {'N': str(now)},
        }
    )
    print(f'initialized {user_id} account={account_id} budget=${args.budget_usd}')

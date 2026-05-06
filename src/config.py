import os
from decimal import Decimal

USERS_TABLE = os.getenv('USERS_TABLE', 'c4g-budget-users')
ACTIVE_RESOURCES_TABLE = os.getenv('ACTIVE_RESOURCES_TABLE', 'c4g-active-resources')
USAGE_LOG_TABLE = os.getenv('USAGE_LOG_TABLE', 'c4g-usage-log')
PRICE_CACHE_TABLE = os.getenv('PRICE_CACHE_TABLE', 'c4g-price-cache')
NOTIFICATION_LOCKS_TABLE = os.getenv('NOTIFICATION_LOCKS_TABLE', 'c4g-notification-locks')
SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN', '')
MEMBER_ROLE_NAME = os.getenv('MEMBER_ROLE_NAME', 'C4GBudgetMemberRole')
EXTERNAL_ID = os.getenv('EXTERNAL_ID', '')
DEFAULT_BUDGET_MICROS = int(os.getenv('DEFAULT_BUDGET_MICROS', '2000000'))
WARN_80_MICROS = int(Decimal(DEFAULT_BUDGET_MICROS) * Decimal('0.80'))
PRESTOP_95_MICROS = int(Decimal(DEFAULT_BUDGET_MICROS) * Decimal('0.95'))
HARDLOCK_100_MICROS = int(DEFAULT_BUDGET_MICROS)
MANAGEMENT_REGION = os.getenv('MANAGEMENT_REGION', 'us-east-1')
REGIONS = [r.strip() for r in os.getenv('REGIONS', 'us-east-1,us-east-2,us-west-2,ap-south-1').split(',') if r.strip()]
PRESTOP_SCP_ID = os.getenv('PRESTOP_SCP_ID', '')
HARDLOCK_SCP_ID = os.getenv('HARDLOCK_SCP_ID', '')
ALLOW_SAGEMAKER_ENDPOINT_DELETE = os.getenv('ALLOW_SAGEMAKER_ENDPOINT_DELETE', 'false').lower() == 'true'
SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', 'labs@cloud4green.com')
METER_WINDOW_SECONDS = int(os.getenv('METER_WINDOW_SECONDS', '300'))
EVENT_ID_TTL_SECONDS = int(os.getenv('EVENT_ID_TTL_SECONDS', str(7 * 24 * 3600)))
NOTIFICATION_TTL_SECONDS = int(os.getenv('NOTIFICATION_TTL_SECONDS', str(24 * 3600)))
BEDROCK_PROXY_REQUIRED_HEADER = os.getenv('BEDROCK_PROXY_REQUIRED_HEADER', 'x-c4g-user-id')
SAFETY_FALLBACK_RATE_MICROS_PER_SECOND = int(os.getenv('SAFETY_FALLBACK_RATE_MICROS_PER_SECOND', '10'))

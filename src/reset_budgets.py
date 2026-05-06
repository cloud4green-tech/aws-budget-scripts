import logging
from budget_manager import list_users, init_or_reset_user
from enforcement_engine import reset_account
from config import DEFAULT_BUDGET_MICROS

log = logging.getLogger(__name__)

def lambda_handler(event, context):
    count = 0
    for user in list_users():
        reset_account(user)
        init_or_reset_user(user['user_id'], user['account_id'], user.get('email',''), DEFAULT_BUDGET_MICROS)
        count += 1
    return {'reset_users': count, 'budget_total_micros': DEFAULT_BUDGET_MICROS}

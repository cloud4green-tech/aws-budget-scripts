import logging
from decimal import Decimal

from budget_manager import get_user, update_threshold_state
from sns_notifier import notify_once
from enforcement_engine import apply_pre_stop, apply_hard_lock

log = logging.getLogger(__name__)

def evaluate_thresholds(user_id: str):
    user = get_user(user_id)
    if not user:
        return None
    total = user['budget_total_micros']
    used = user['budget_used_micros'] + user.get('reserved_micros', 0)
    if total <= 0:
        return None
    pct = Decimal(used) / Decimal(total)
    current_level = int(user.get('threshold_level') or '0')
    account_id = user['account_id']

    if pct >= Decimal('1.0') and current_level < 100:
        notify_once(user, '100', used, total)
        apply_hard_lock(user)
        update_threshold_state(user_id, 'HARD_LOCK', '100')
        return '100'

    if pct >= Decimal('0.95') and current_level < 95:
        notify_once(user, '95', used, total)
        apply_pre_stop(user)
        update_threshold_state(user_id, 'PRE_STOP', '95')
        return '95'

    if pct >= Decimal('0.80') and current_level < 80:
        notify_once(user, '80', used, total)
        update_threshold_state(user_id, 'WARNING', '80')
        return '80'

    return user.get('threshold_level')

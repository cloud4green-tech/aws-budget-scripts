import hashlib
import json
import logging
import time
from decimal import Decimal
from typing import Any, Dict

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)

def now_epoch() -> int:
    return int(time.time())

def stable_hash(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()

def micros(amount_dollars: float) -> int:
    return int(Decimal(str(amount_dollars)) * Decimal('1000000'))

def dollars(micros_value: int) -> float:
    return float(Decimal(micros_value) / Decimal('1000000'))

def response(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'statusCode': status,
        'headers': {'content-type': 'application/json'},
        'body': json.dumps(body, cls=DecimalEncoder),
    }

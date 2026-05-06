
def discover(account_id: str, region: str):
    return []

def stop_or_pause(account_id: str, region: str, hard: bool = False):
    return [{'service': 'dynamodb', 'region': region, 'note': 'no tables deleted; writes are blocked by SCP at threshold'}]

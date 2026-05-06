
def discover(account_id: str, region: str):
    return []

def stop_or_pause(account_id: str, region: str, hard: bool = False):
    return [{'service': 'bedrock', 'region': region, 'note': 'Bedrock resources are not deleted; inference and create/update actions are blocked by SCP/proxy'}]

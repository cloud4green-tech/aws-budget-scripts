import json
from typing import Any, Dict

def parse_converse_usage(resp: Dict[str, Any]) -> Dict[str, int]:
    usage = resp.get('usage', {}) or {}
    return {
        'input_tokens': int(usage.get('inputTokens', usage.get('input_tokens', 0)) or 0),
        'output_tokens': int(usage.get('outputTokens', usage.get('output_tokens', 0)) or 0),
        'cache_read_tokens': int(usage.get('cacheReadInputTokens', usage.get('cache_read_input_tokens', 0)) or 0),
        'cache_write_tokens': int(usage.get('cacheWriteInputTokens', usage.get('cache_write_input_tokens', 0)) or 0),
    }

def parse_invoke_body_usage(body_bytes: bytes) -> Dict[str, int]:
    try:
        body = json.loads(body_bytes.decode('utf-8'))
    except Exception:
        return {'input_tokens': 0, 'output_tokens': 0, 'cache_read_tokens': 0, 'cache_write_tokens': 0}
    usage = body.get('usage') or body.get('amazon-bedrock-invocationMetrics') or {}
    if 'input_tokens' in usage or 'output_tokens' in usage:
        return {'input_tokens': int(usage.get('input_tokens', 0) or 0), 'output_tokens': int(usage.get('output_tokens', 0) or 0), 'cache_read_tokens': int(usage.get('cache_read_input_tokens', 0) or 0), 'cache_write_tokens': int(usage.get('cache_creation_input_tokens', 0) or 0)}
    if 'inputTokenCount' in usage or 'outputTokenCount' in usage:
        return {'input_tokens': int(usage.get('inputTokenCount', 0) or 0), 'output_tokens': int(usage.get('outputTokenCount', 0) or 0), 'cache_read_tokens': 0, 'cache_write_tokens': 0}
    if 'usage' in body:
        return parse_converse_usage({'usage': body['usage']})
    return {'input_tokens': 0, 'output_tokens': 0, 'cache_read_tokens': 0, 'cache_write_tokens': 0}

def parse_stream_events(events) -> Dict[str, Any]:
    chunks = []
    usage = {'input_tokens': 0, 'output_tokens': 0, 'cache_read_tokens': 0, 'cache_write_tokens': 0}
    for event in events:
        if 'chunk' in event and event['chunk'].get('bytes'):
            b = event['chunk']['bytes']
            chunks.append(b)
            try:
                payload = json.loads(b.decode('utf-8'))
                if 'metadata' in payload and 'usage' in payload['metadata']:
                    usage.update(parse_converse_usage({'usage': payload['metadata']['usage']}))
                elif 'usage' in payload:
                    usage.update(parse_converse_usage(payload))
            except Exception:
                pass
        elif 'metadata' in event and 'usage' in event['metadata']:
            usage.update(parse_converse_usage({'usage': event['metadata']['usage']}))
    return {'body': b''.join(chunks), 'usage': usage}

import base64
import json
import logging
from typing import Dict, Any
import boto3

from config import BEDROCK_PROXY_REQUIRED_HEADER, SUPPORT_EMAIL
from budget_manager import get_user, reserve_budget, finalize_reservation, refund_reservation, available_micros
from threshold_handler import evaluate_thresholds
from utils import response, stable_hash
from bedrock.bedrock_cost_calculator import reserve_amount_for_request, calculate_token_cost_micros
from bedrock.bedrock_token_usage_parser import parse_converse_usage, parse_invoke_body_usage, parse_stream_events

log = logging.getLogger(__name__)

FRIENDLY_95 = 'Your services are going to stop because you are about to hit your assigned budget.'
FRIENDLY_100 = f'You have hit your assigned budget. Contact support team {SUPPORT_EMAIL} or your administrator'


def _headers(event):
    return {str(k).lower(): v for k, v in (event.get('headers') or {}).items()}


def _parse_body(event):
    body = event.get('body') or '{}'
    if event.get('isBase64Encoded'):
        body = base64.b64decode(body).decode('utf-8')
    return json.loads(body)


def _max_tokens(payload: Dict[str, Any]) -> int:
    for path in [
        ('inferenceConfig', 'maxTokens'),
        ('inferenceConfig', 'max_tokens'),
        ('body', 'max_tokens'),
        ('body', 'maxTokens'),
        ('body', 'max_new_tokens'),
        ('body', 'max_gen_len'),
    ]:
        cur = payload
        ok = True
        for p in path:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                ok = False
                break
        if ok:
            try:
                return int(cur)
            except Exception:
                pass
    return int(payload.get('maxTokens', 1024))


def _count_tokens(brt, operation: str, model_id: str, payload: Dict[str, Any]) -> int:
    try:
        if operation in ('Converse', 'ConverseStream'):
            count_input = {'converse': {'messages': payload.get('messages', []), 'system': payload.get('system', [])}}
        else:
            body = payload.get('body', payload)
            count_input = {'invokeModel': {'body': json.dumps(body).encode('utf-8') if not isinstance(body, (bytes, bytearray)) else body}}
        resp = brt.count_tokens(modelId=model_id, input=count_input)
        return int(resp.get('inputTokens', 0))
    except Exception:
        log.exception('CountTokens failed; using conservative estimate')
        # Safe fallback when CountTokens is not available for a specific model/API shape.
        return 4000


def lambda_handler(event, context):
    try:
        h = _headers(event)
        user_id = h.get(BEDROCK_PROXY_REQUIRED_HEADER.lower()) or h.get('x-c4g-user-id')
        if not user_id:
            return response(401, {'message': 'Missing Cloud4Green user header.'})
        user = get_user(user_id)
        if not user:
            return response(404, {'message': 'Budget profile not found. Contact your lab administrator.'})
        if user.get('threshold_level') == '100' or available_micros(user_id) <= 0:
            return response(402, {'message': FRIENDLY_100})

        payload = _parse_body(event)
        operation = payload.get('operation', 'Converse')
        region = payload.get('region') or user.get('region') or 'us-east-1'
        model_id = payload.get('modelId') or payload.get('model_id')
        if not model_id:
            return response(400, {'message': 'modelId is required'})
        brt = boto3.client('bedrock-runtime', region_name=region)

        input_tokens = _count_tokens(brt, operation, model_id, payload)
        max_output_tokens = _max_tokens(payload)
        reserve_micros = reserve_amount_for_request(model_id, region, input_tokens, max_output_tokens)
        ok, reservation_id = reserve_budget(user_id, reserve_micros, f'{operation}:{model_id}')
        if not ok:
            evaluate_thresholds(user_id)
            return response(402, {'message': FRIENDLY_95, 'available_micros': available_micros(user_id), 'required_reserve_micros': reserve_micros})

        actual_usage = {'input_tokens': input_tokens, 'output_tokens': max_output_tokens, 'cache_read_tokens': 0, 'cache_write_tokens': 0}
        try:
            if operation == 'Converse':
                resp = brt.converse(modelId=model_id, messages=payload.get('messages', []), system=payload.get('system', []), inferenceConfig=payload.get('inferenceConfig', {}))
                actual_usage = parse_converse_usage(resp)
                body = resp
            elif operation == 'ConverseStream':
                stream = brt.converse_stream(modelId=model_id, messages=payload.get('messages', []), system=payload.get('system', []), inferenceConfig=payload.get('inferenceConfig', {}))
                parsed = parse_stream_events(stream.get('stream', []))
                actual_usage = parsed['usage'] if parsed['usage'].get('output_tokens') else actual_usage
                body = {'streamBufferedBase64': base64.b64encode(parsed['body']).decode('ascii'), 'usage': actual_usage}
            elif operation == 'InvokeModel':
                model_body = payload.get('body', {})
                resp = brt.invoke_model(modelId=model_id, body=json.dumps(model_body).encode('utf-8'), contentType=payload.get('contentType', 'application/json'), accept=payload.get('accept', 'application/json'))
                b = resp['body'].read()
                actual_usage = parse_invoke_body_usage(b)
                if actual_usage['input_tokens'] == 0:
                    actual_usage['input_tokens'] = input_tokens
                body = {'bodyBase64': base64.b64encode(b).decode('ascii'), 'contentType': resp.get('contentType', 'application/json'), 'usage': actual_usage}
            elif operation == 'InvokeModelWithResponseStream':
                model_body = payload.get('body', {})
                resp = brt.invoke_model_with_response_stream(modelId=model_id, body=json.dumps(model_body).encode('utf-8'), contentType=payload.get('contentType', 'application/json'), accept=payload.get('accept', 'application/json'))
                parsed = parse_stream_events(resp.get('body', []))
                actual_usage = parsed['usage'] if parsed['usage'].get('output_tokens') else actual_usage
                body = {'streamBufferedBase64': base64.b64encode(parsed['body']).decode('ascii'), 'usage': actual_usage}
            elif operation == 'CountTokens':
                body = {'inputTokens': input_tokens}
                actual_usage = {'input_tokens': input_tokens, 'output_tokens': 0, 'cache_read_tokens': 0, 'cache_write_tokens': 0}
            else:
                refund_reservation(user_id, reservation_id)
                return response(400, {'message': f'Unsupported proxy operation: {operation}'})
        except Exception as e:
            refund_reservation(user_id, reservation_id)
            log.exception('Bedrock proxy call failed')
            return response(502, {'message': 'Bedrock request failed. Your reserved budget was refunded.', 'error': str(e)[:500]})

        actual_micros = calculate_token_cost_micros(model_id, region, **actual_usage)
        usage_event_id = 'bedrock-proxy-' + stable_hash({'user': user_id, 'reservation': reservation_id, 'model': model_id, 'usage': actual_usage})
        finalize_reservation(user_id, reservation_id, actual_micros, {
            'event_id': usage_event_id,
            'user_id': user_id,
            'account_id': user.get('account_id', 'proxy'),
            'service': 'bedrock',
            'region': region,
            'event_name': operation,
            'resource_id': model_id,
            'pricing_source': 'bedrock_proxy_actual_usage',
        })
        threshold = evaluate_thresholds(user_id)
        return response(200, {'message': 'ok', 'modelId': model_id, 'operation': operation, 'usage': actual_usage, 'cost_micros': actual_micros, 'threshold': threshold, 'bedrock': body})
    except Exception as e:
        log.exception('proxy fatal')
        return response(500, {'message': 'Budget proxy failed. Contact lab administrator.', 'error': str(e)[:500]})

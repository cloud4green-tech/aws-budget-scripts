from utils import response
from budget_manager import init_or_reset_user, get_user, list_users
from config import DEFAULT_BUDGET_MICROS


def lambda_handler(event, context):
    method = event.get('requestContext', {}).get('http', {}).get('method') or event.get('httpMethod', 'GET')
    path = event.get('rawPath') or event.get('path', '/')
    if method == 'GET' and path.endswith('/users'):
        return response(200, {'users': list(list_users())})
    return response(404, {'message': 'not found'})

import juno
import orjson
from odoo.exceptions import ValidationError
from odoo.http import request, Response


def validate_required_fields(data, required_fields):
    error_fields = [field for field in required_fields if field not in data]
    return error_fields


def return_error_http(http_code, msg):
    return Response(
        orjson.dumps({"result": "error", "message": msg}),
        status=http_code,
        content_type="application/json"
    )

def return_success(msg=None, **kwargs):
    return Response(
        orjson.dumps({"result": "Ok", "message": 'Success' or msg, **kwargs}),
        status=200,
        content_type="application/json"
    )

# IUGU utils
def iugu_get_invoice_api(token=None):
    if not token:
        raise ValidationError('Sem o Token de Parâmetro para consulta no IUGU')
    iugu.config(token=token)
    return iugu.Invoice()

def iugu_get_subscription(token=None):
    if not token:
        raise ValidationError('Sem o Token de Parâmetro para consulta no IUGU')
    iugu.config(token=token)
    return iugu.Subscription()


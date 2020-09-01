import logging
import requests
import json

from odoo import http
from odoo.http import request
from werkzeug.utils import redirect

_logger = logging.getLogger(__name__)


class MercadoPagoController(http.Controller):
    @http.route(
        [
            "/mercadopago/notificacao",
            "/mercadopago/notificacao/<string:status>",
        ],
        type="http",
        auth="none",
        methods=["GET", "POST"],
        csrf=False,
    )
    def mercadopago_notificacao(self, status=False, **kw):
        if status:
            post = {"status": status, "preference_id": kw.get("preference_id")}
        elif kw.get("topic") == "payment" and kw.get("id"):
            transaction = (
                request.env["payment.acquirer"]
                .sudo()
                .search([("acquirer_reference", "=", kw.get("id"))])
            )
            api_token = transaction.acquirer_id.mercadopago_access_token
            response = requests.request(
                "GET",
                url="https://api.mercadopago.com/v1/payments/{}".format(
                    transaction.acquirer_reference
                ),
                params=json.dumps({"access_token": api_token}),
            )

            post = response.json()

        request.env["payment.transaction"].sudo().form_feedback(
            post, "mercadopago"
        )
        return redirect("/payment/process")

    @http.route(
        "/mercadopago/checkout/redirect",
        type="http",
        auth="none",
        methods=["GET", "POST"],
    )
    def mercadopago_checkout_redirect(self, **post):
        post = post
        if "secure_url" in post:
            return redirect(post["secure_url"])

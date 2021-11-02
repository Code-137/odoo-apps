import logging
import pprint
import json
import requests

from odoo import http
from odoo.http import request
from werkzeug.utils import redirect

_logger = logging.getLogger(__name__)


class PagHiperController(http.Controller):
    @http.route(
        "/paghiper/notificacao/",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def paghiper_notificacao(self, **post):
        # TODO Still needs to be tested
        transaction = (
            request.env["payment.transaction"]
            .sudo()
            .search([("acquirer_reference", "=", post.get("transaction_id"))])
        )

        data = {
            "token": transaction.acquirer_id.paghiper_api_token,
            "apiKey": post.get("apiKey"),
            "transaction_id": post.get("transaction_id"),
            "notification_id": post.get("notification_id"),
        }

        url = " https://api.paghiper.com/transaction/notification/"
        headers = {"content-type": "application/json"}

        res = requests.request(
            "POST", url, headers=headers, data=json.dumps(data)
        )

        data = res.json().get("status_request")

        if data.get("result") == "success":
            tx = (
                request.env["payment.transaction"]
                .sudo()
                ._get_tx_from_feedback_data("paghiper", post)
            )

            tx.sudo()._handle_feedback_data("paghiper", post)
        else:
            _logger.warn(
                "Error PagHiper Webhook: {}".format(
                    data.get("response_message")
                )
            )

    @http.route(
        ["/payment/paghiper/feedback"],
        type="http",
        auth="public",
        methods=["GET", "POST"],
        csrf=False,
    )
    def paghiper_form_feedback(self, **post):
        _logger.info(
            "Beginning form_feedback with post data %s", pprint.pformat(post)
        )
        tx = (
            request.env["payment.transaction"]
            .sudo()
            ._get_tx_from_feedback_data("paghiper", post)
        )
        tx.sudo()._handle_feedback_data("paghiper", post)
        return redirect("/payment/status")

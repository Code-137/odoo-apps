import logging
import requests
from odoo import http
from odoo.http import request
from werkzeug.utils import redirect

_logger = logging.getLogger(__name__)


class PicPayController(http.Controller):
    @http.route(
        "/payment/picpay/feedback/<string:reference>",
        type="http",
        auth="public",
        methods=["GET", "POST"],
        csrf=False,
    )
    def picpay_process_payment(self, **post):
        acquirer = (
            request.env["payment.acquirer"]
            .sudo()
            .search([("provider", "=", "picpay")])
        )
        reference = post.get("reference")

        headers = {
            "Content-Type": "application/json",
            "x-picpay-token": acquirer.picpay_token,
        }
        url = (
            "https://appws.picpay.com/ecommerce/public/payments/%s/status"
            % reference
        )

        response = requests.get(url, headers=headers)
        response = response.json()

        tx = (
            request.env["payment.transaction"]
            .sudo()
            ._get_tx_from_feedback_data("picpay", response)
        )
        tx.sudo()._handle_feedback_data("picpay", response)
        return redirect("/payment/status")

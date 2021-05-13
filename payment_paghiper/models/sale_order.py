import logging
import json
import requests

from odoo import models, _

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        for order in self:
            for transaction_id in order.transaction_ids:
                if (
                    transaction_id
                    and transaction_id.acquirer_id.provider == "paghiper"
                ):
                    acquirer = transaction_id.acquirer_id
                    url = "https://api.paghiper.com/transaction/cancel/"
                    headers = {"content-type": "application/json"}

                    vals = {
                        "token": acquirer.paghiper_api_token,
                        "apiKey": acquirer.paghiper_api_key,
                        "status": "canceled",
                        "transaction_id": transaction_id.acquirer_reference,
                    }

                    response = requests.request(
                        "POST", url, headers=headers, data=json.dumps(vals)
                    )

                    data = response.json().get("cancellation_request")

                    if data.get("result") == "success":
                        order.message_post(body=data.get("response_message"))
                    else:
                        error_msg = "Erro ao cancelar boleto no PagHiper: {}"
                        order.message_post(
                            body=_(
                                error_msg.format(data.get("response_message"))
                            )
                        )

        return res

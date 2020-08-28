import requests
from odoo import models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        for order in self:
            for transaction_id in order.transaction_ids:
                if (
                    transaction_id
                    and transaction_id.acquirer_id.provider == "picpay"
                ):
                    headers = {
                        "Content-Type": "application/json",
                        "x-picpay-token":
                            transaction_id.acquirer_id.picpay_token,
                    }
                    url = "https://appws.picpay.com/ecommerce/public/payments/\
{}/cancellations".format(
                        transaction_id.acquirer_reference
                    )
                    body = {}
                    if transaction_id.picpay_authorizarion:
                        body = {
                            "authorizationId":
                                transaction_id.picpay_authorizarion
                        }
                    response = requests.get(
                        url=url, headers=headers, body=body
                    )

                    if not response.ok:
                        data = response.json()
                        msg = "Erro ao cancelar o pagamento PicPay: \
{}\r\n".format(data.get("message"))
                        if response.status_code == 422:
                            msg += "\r\n".join(
                                ["{}: {}".format(err.field, err.message)]
                                for err in data.get("errors")
                            )
                        raise UserError(msg)

        return res

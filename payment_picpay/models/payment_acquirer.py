import json
import logging
import requests

from odoo import fields, models
from odoo.exceptions import UserError
from werkzeug import urls


_logger = logging.getLogger(__name__)


class PicPayAcquirer(models.Model):
    _inherit = "payment.acquirer"

    provider = fields.Selection(
        selection_add=[("picpay", "PicPay")],
        ondelete={"picpay": "set default"},
    )
    picpay_token = fields.Char("PicPay Token")
    picpay_seller_token = fields.Char("PicPay Seller Token")

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != "picpay":
            return super()._get_default_payment_method_id()
        return self.env.ref("payment_picpay.payment_method_picpay").id

    def _picpay_make_request(self, values):
        """ Função para gerar HTML POST do Iugu """
        # base_url = (
        # self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        # )
        base_url = "http://odoo15.localhost"
        partner = self.env["res.partner"].browse(values.get("partner_id"))
        pic_vals = {
            "referenceId": values.get("reference"),
            "callbackUrl": "%s/payment/picpay/feedback" % base_url,
            "returnUrl": "%s/payment/picpay/feedback/%s"
            % (base_url, values.get("reference")),
            "value": values.get("amount"),
            "buyer": {
                "firstName": values.get("partner_first_name"),
                "lastName": values.get("partner_last_name"),
                "document": partner.l10n_br_cnpj_cpf,
                "email": values.get("billing_partner_email"),
                "phone": values.get("billing_partner_phone"),
            },
        }
        headers = {
            "Content-Type": "application/json",
            "x-picpay-token": self.picpay_token,
        }
        url = "https://appws.picpay.com/ecommerce/public/payments"
        response = requests.post(
            url, data=json.dumps(pic_vals), headers=headers
        )

        data = response.json()

        if not response.ok:
            raise UserError(data.get("message"))

        acquirer_reference = data.get("referenceId")
        payment_transaction_id = self.env["payment.transaction"].search(
            [("reference", "=", values["reference"])]
        )

        payment_transaction_id.write(
            {
                "acquirer_reference": acquirer_reference,
                "picpay_url": data["paymentUrl"],
            }
        )

        res = {"api_url": data["paymentUrl"]}

        res.update(data)

        return res

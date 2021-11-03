import re
import logging
from mercadopago import MP

from odoo import fields, models
from odoo.http import request
from werkzeug import urls

_logger = logging.getLogger(__name__)
odoo_request = request


class MercadopagoBoleto(models.Model):
    _inherit = "payment.acquirer"

    provider = fields.Selection(
        selection_add=[("mercadopago", "Mercado Pago")],
        ondelete={"mercadopago": "set default"},
    )
    mercadopago_public_key = fields.Char("Mercado Pago Public Key")
    mercadopago_access_token = fields.Char("Mercado Pago Access Token")

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != "mercadopago":
            return super()._get_default_payment_method_id()
        return self.env.ref(
            "payment_mercadopago.payment_method_mercadopago"
        ).id

    def _mercadopago_make_request(self, values):
        """ Função para gerar HTML POST do mercadopago """
        base_url = (
            self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        )

        partner_id = self.env["res.partner"].browse(values.get("partner_id"))
        commercial_partner_id = partner_id.commercial_partner_id

        items = [
            {
                "title": "Fatura Ref: %s" % values.get("reference"),
                "quantity": 1,
                "unit_price": int(values.get("amount")),
                "currency_id": "BRL",
            }
        ]

        payer = {
            "name": commercial_partner_id.name,
            "email": commercial_partner_id.email,
            "identification": {
                "type": "CPF"
                if commercial_partner_id.company_type == "person"
                else "CNPJ",
                "number": re.sub(
                    "[^0-9]", "", commercial_partner_id.l10n_br_cnpj_cpf or ""
                ),
            },
            "address": {
                "street_name": commercial_partner_id.street,
                "street_number": commercial_partner_id.l10n_br_number,
                "zip_code": commercial_partner_id.zip,
            },
        }

        preference = {
            "external_reference": values.get("reference"),
            "auto_return": "all",
            "back_urls": {
                "success": urls.url_join(
                    base_url, "/mercadopago/notificacao/approved"
                ),
                "pending": urls.url_join(
                    base_url, "/mercadopago/notificacao/pending"
                ),
                "failure": urls.url_join(
                    base_url, "/mercadopago/notificacao/failure"
                ),
            },
            "items": items,
            "payer": payer,
        }

        mp = MP(self.mercadopago_access_token)

        result = mp.create_preference(preference)

        url = result["response"]["init_point"]
        acquirer_reference = result["response"]["id"]

        payment_transaction_id = self.env["payment.transaction"].search(
            [("reference", "=", values["reference"])]
        )

        payment_transaction_id.write(
            {"acquirer_reference": acquirer_reference}
        )

        return {
            # "": urls.url_join(
            # base_url, "/mercadopago/checkout/redirect"
            # ),
            "api_url": url,
        }

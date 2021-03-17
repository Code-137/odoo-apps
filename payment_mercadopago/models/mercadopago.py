import re
import logging
from mercadopago import MP

from odoo import api, fields, models
from odoo.http import request
from werkzeug import urls

_logger = logging.getLogger(__name__)
odoo_request = request


class MercadopagoBoleto(models.Model):
    _inherit = "payment.acquirer"

    provider = fields.Selection(
        selection_add=[("mercadopago", "Mercado Pago")]
    )
    mercadopago_public_key = fields.Char("Mercado Pago Public Key")
    mercadopago_access_token = fields.Char("Mercado Pago Access Token")

    def mercadopago_form_generate_values(self, values):
        """ Função para gerar HTML POST do mercadopago """
        base_url = (
            self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        )

        partner_id = values.get("billing_partner")
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
            "checkout_url": urls.url_join(
                base_url, "/mercadopago/checkout/redirect"
            ),
            "secure_url": url,
        }


class TransactionMercadopago(models.Model):
    _inherit = "payment.transaction"

    @api.model
    def _mercadopago_form_get_tx_from_data(self, data):
        acquirer_reference = data.get("preference_id")
        tx = self.search([("acquirer_reference", "=", acquirer_reference)])
        return tx[0]

    def _mercadopago_form_validate(self, data):
        status = data.get("status")

        if status in ("paid", "partially_paid", "approved", "authorized"):
            self._set_transaction_done()
            return True
        elif status == "pending":
            self._set_transaction_pending()
            return True
        else:
            self._set_transaction_cancel()
            return False

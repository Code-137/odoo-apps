import re
import logging
import json
import requests

from odoo import fields, models, _
from odoo.http import request
from odoo.exceptions import UserError
from werkzeug import urls

_logger = logging.getLogger(__name__)
odoo_request = request


class PagHiperBoleto(models.Model):
    _inherit = "payment.acquirer"

    provider = fields.Selection(
        selection_add=[("paghiper", "PagHiper")],
        ondelete={"paghiper": "set default"},
    )
    paghiper_api_key = fields.Char("PagHiper Api Key")
    paghiper_api_token = fields.Char("PagHiper Api Token", size=100)

    def paghiper_get_form_action_url(self):
        return "/payment/paghiper/feedback"

    def _paghiper_make_request(self, values=None):
        """ Função para gerar HTML POST do PagHiper """
        base_url = (
            self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        )

        partner_id = values.get("billing_partner")
        commercial_partner_id = partner_id.commercial_partner_id

        items = [
            {
                "item_id": 1,
                "description": "Fatura Ref: %s" % values.get("reference"),
                "quantity": 1,
                "price_cents": int(values.get("amount") * 100),
            },
        ]
        invoice_data = {
            "apiKey": self.paghiper_api_key,
            "type_bank_slip": "boletoA4",
            "order_id": values.get("reference"),
            "days_due_date": 3,
            "notification_url": urls.url_join(
                base_url, "/paghiper/notificacao/"
            ),
            "items": items,
            "payer_name": commercial_partner_id.name,
            "payer_email": partner_id.email,
            "payer_cpf_cnpj": commercial_partner_id.l10n_br_cnpj_cpf,
            "payer_phone": commercial_partner_id.phone,
            "payer_street": commercial_partner_id.street or "",
            "payer_city": commercial_partner_id.city_id.name or "",
            "payer_number": commercial_partner_id.l10n_br_number or "",
            "payer_state": commercial_partner_id.state_id.l10n_br_ibge_code
            or "",
            "payer_complement": commercial_partner_id.street2 or "",
            "payer_zip_code": re.sub(
                "[^0-9]", "", commercial_partner_id.zip or ""
            ),
            "late_payment_fine": 2,
            "per_day_interest": True,
        }

        url = "https://api.paghiper.com/transaction/create/"
        headers = {"content-type": "application/json"}
        payload = json.dumps(invoice_data)
        response = requests.request("POST", url, data=payload, headers=headers)
        if response.status_code == 200:
            json_resp = response.json()
            raise UserError(json_resp["create_request"]["response_message"])
        elif response.status_code in (401, 405):
            raise UserError(
                _("Configure corretamente as credenciais do PagHiper")
            )
        if response.status_code != 201:
            raise UserError(_("Erro ao se conectar com o PagHiper"))

        result = response.json()
        acquirer_reference = result["create_request"]["transaction_id"]
        payment_transaction_id = self.env["payment.transaction"].search(
            [("reference", "=", values["reference"])]
        )

        payment_transaction_id.write(
            {
                "acquirer_reference": acquirer_reference,
                "boleto_url": result["create_request"]["bank_slip"][
                    "url_slip"
                ],
                "boleto_digitable_line": result["create_request"]["bank_slip"][
                    "digitable_line"
                ],
            }
        )

        res = {
            "checkout_url": "/payment/paghiper/feedback",
        }

        res.update(result)

        return result

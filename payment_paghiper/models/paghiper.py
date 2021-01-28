import re
import logging
import json
import requests

from odoo import api, fields, models, _
from odoo.http import request
from odoo.exceptions import UserError
from werkzeug import urls

_logger = logging.getLogger(__name__)
odoo_request = request


class PagHiperBoleto(models.Model):
    _inherit = "payment.acquirer"

    provider = fields.Selection(selection_add=[("paghiper", "PagHiper")])
    paghiper_api_key = fields.Char("PagHiper Api Key")
    paghiper_api_token = fields.Char("PagHiper Api Token", size=100)

    def paghiper_get_form_action_url(self):
        return "/payment/paghiper/feedback"

    def paghiper_form_generate_values(self, values):
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
            }
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

        return res


class TransactionPagHiper(models.Model):
    _inherit = "payment.transaction"

    boleto_url = fields.Char(string="Fatura", size=300)
    boleto_digitable_line = fields.Char(string="Linha Digitável")

    @api.model
    def _paghiper_form_get_tx_from_data(self, data):
        acquirer_reference = data.get("transaction_id")
        tx = self.search([("acquirer_reference", "=", acquirer_reference)])
        return tx[0]

    def _paghiper_form_validate(self, data):
        status = data.get("status")

        if status in ("paid", "partially_paid", "authorized"):
            self._set_transaction_done()
            return True
        elif status in ("pending", "Aguardando"):
            self._set_transaction_pending()
            return True
        else:
            _logger.info(
                "Cancelling PagHiper transaction: {}".format(
                    self.acquirer_reference
                )
            )
            allowed_states = ("draft", "pending", "authorized")
            target_state = "cancel"
            (
                tx_to_process,
                tx_already_processed,
                tx_wrong_state,
            ) = self._filter_transaction_state(allowed_states, target_state)
            for tx in tx_already_processed:
                _logger.info(
                    "Trying to write the same state twice on tx (ref: %s,"
                    "state: %s" % (tx.reference, tx.state)
                )
            for tx in tx_wrong_state:
                _logger.warning(
                    "Processed tx with abnormal state (ref: %s, target state:"
                    " %s, previous state %s, expected previous states: %s)"
                    % (tx.reference, target_state, tx.state, allowed_states)
                )

            tx_to_process.mapped("payment_id").cancel()

            tx_to_process.write(
                {"state": target_state, "date": fields.Datetime.now()}
            )
            tx_to_process._log_payment_transaction_received()
            return False

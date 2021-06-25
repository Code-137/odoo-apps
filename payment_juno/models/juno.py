# License MIT (https://mit-license.org/)

import logging
import juno
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AcquirerJuno(models.Model):
    _inherit = "payment.acquirer"

    provider = fields.Selection(selection_add=[("juno", "Juno")])

    @api.multi
    def juno_form_generate_values(self, tx_values):
        """Função para gerar HTML POST da Juno"""
        charge = {
            "pixKey": "",
            "pixIncludeImage": True,
            "description": tx_values["reference"],
            "references": [tx_values["reference"]],
            "amount": tx_values["amount"],
            "dueDate": tx_values["date_maturity"],
            "maxOverdueDays": 0,
            "fine": 0,
            "interest": "0.00",
            "discountAmount": "0.00",
            "discountDays": -1,
            "paymentTypes": ["BOLETO", "CREDIT_CARD"],
        }
        billing = {
            "name": tx_values["partner"].name,
            "document": tx_values["partner"].cnpj_cpf,
            "email": tx_values["partner"].email,
            "address": {
                "street": tx_values["partner"].street,
                "number": tx_values["partner"].number,
                "complement": tx_values["partner"].street2 or "",
                "neighborhood": tx_values["partner"].district or "",
                "city": tx_values["partner"].city_id.name,
                "state": tx_values["partner"].state_id.code,
                "postCode": tx_values["partner"].zip,
            },
            "phone": tx_values["partner"].phone or "",
        }
        vals = {"charge": charge, "billing": billing}

        company = self.env.user.company_id
        juno_client_id = company.juno_client_id
        juno_client_secret = company.juno_client_secret
        juno_token = company.juno_api_token
        juno_environment = company.juno_environment
        juno.init(
            client_id=juno_client_id,
            client_secret=juno_client_secret,
            resource_token=juno_token,
            sandbox=juno_environment,
        )

        response = juno.charge.create(vals)

        if not response.is_success:
            errors = ""
            for error in response.errors:
                errors += error + " /n"

            raise Exception(_("Error to communicate with Juno /n" + errors))

        return {"checkout_url": response.charge.checkout_url}


class TransactionJuno(models.Model):
    _inherit = "payment.transaction"

    transaction_url = fields.Char(string="Url de Pagamento", size=256)
    date_maturity = fields.Date(string="Data de Vencimento")
    juno_transaction_id = fields.Char(string="Transaction ID")


    def cron_verify_transaction(self):
        documents = self.search(
            [
                ("state", "in", ["draft", "pending"]),
            ],
            limit=50,
        )
        for doc in documents:
            try:
                doc.action_verify_transaction()
                self.env.cr.commit()
            except Exception as e:
                self.env.cr.rollback()
                _logger.exception(
                    "Payment Transaction ID {}: {}.".format(doc.id, str(e)),
                    exc_info=True,
                )

    def action_verify_transaction(self):
        if self.acquirer_id.provider != "juno":
            return
        if not self.acquirer_reference:
            raise UserError(
                "Esta transação não foi enviada a nenhum gateway de pagamento"
            )
        client_id = self.env.company.juno_client_id
        client_secret = self.env.company.juno_client_secret
        token = self.env.company.juno_api_token
        environment = self.env.company.juno_environment

        juno.init(
            client_id=client_id,
            client_secret=client_secret,
            resource_token=token,
            environment=environment,
        )

        result = juno.charge.find_by_id(self.acquirer_reference)

        if not result.is_success:
            errors = ""
            for error in result.errors:
                errors += errors + " /n"

            raise UserError(errors)

        if result.charge.status == "PAID" and self.state not in (
            "done",
            "authorized",
        ):
            self._set_transaction_done()
            self._post_process_after_done()
        else:
            self.juno_status = self.charge.status

    def cancel_transaction_in_juno(self):
        if not self.acquirer_reference:
            raise UserError("Esta parcela não foi enviada ao Juno")
        client_id = self.env.company.juno_client_id
        client_secret = self.env.company.juno_client_secret
        token = self.env.company.juno_api_token
        environment = self.env.company.juno_environment

        juno.init(
            client_id=client_id,
            client_secret=client_secret,
            resource_token=token,
            environment=environment,
        )
        juno.charge.cancelation(self.acquirer_reference)

    def action_cancel_transaction(self):
        self._set_transaction_cancel()
        if self.acquirer_id.provider == "juno":
            self.cancel_transaction_in_juno()

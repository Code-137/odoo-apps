import logging

from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class TransactionPicPay(models.Model):
    _inherit = "payment.transaction"

    picpay_url = fields.Char(string="Fatura PicPay", size=300)
    picpay_authorizarion = fields.Char(string="Autorização do Pagamento")

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider != "picpay":
            return res

        acquirer_id = self.env["payment.acquirer"].browse(
            processing_values["acquirer_id"]
        )
        res = acquirer_id._picpay_make_request(processing_values)

        return res

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        tx = super()._get_tx_from_feedback_data(provider, data)

        if provider != "picpay":
            return tx

        acquirer_reference = data.get("referenceId")
        tx = self.search([("acquirer_reference", "=", acquirer_reference)])
        return tx

    def _process_feedback_data(self, data):
        super()._process_feedback_data(data)
        if self.provider != "picpay":
            return

        status = data.get("status")

        if status in ("paid", "completed", "chargeback"):
            self._set_done()
        elif status == "pending":
            self._set_pending()
        else:
            _logger.info(
                "cancelling paghiper transaction: {}".format(
                    self.acquirer_reference
                )
            )
            allowed_states = ("draft", "pending", "authorized")
            target_state = "cancel"
            tx_to_process = self._filter_transaction_state(
                allowed_states, target_state, "payment transaction cancelled"
            )
            tx_to_process.mapped("payment_id").cancel()
            tx_to_process.write(
                {"state": target_state, "date": fields.datetime.now()}
            )
            tx_to_process._log_payment_transaction_received()

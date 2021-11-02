import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class TransactionPagHiper(models.Model):
    _inherit = "payment.transaction"

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider != "paghiper":
            return res

        acquirer_id = self.env["payment.acquirer"].browse(
            processing_values["acquirer_id"]
        )
        res = acquirer_id._paghiper_make_request(processing_values)

        return res

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        tx = super()._get_tx_from_feedback_data(provider, data)

        if provider != "paghiper":
            return tx

        acquirer_reference = data.get("transaction_id")
        tx = self.search([("acquirer_reference", "=", acquirer_reference)])
        return tx[0]

    def _process_feedback_data(self, data):
        status = data.get("status")

        if status in ("paid", "partially_paid", "authorized"):
            self._set_done()
        elif status in ("pending", "Aguardando"):
            self._set_pending()
        else:
            _logger.info(
                "Cancelling PagHiper transaction: {}".format(
                    self.acquirer_reference
                )
            )
            allowed_states = ("draft", "pending", "authorized")
            target_state = "cancel"
            tx_to_process = self._filter_transaction_state(
                allowed_states, target_state, "Payment Transaction Cancelled"
            )
            tx_to_process.mapped("payment_id").cancel()
            tx_to_process.write(
                {"state": target_state, "date": fields.Datetime.now()}
            )
            tx_to_process._log_payment_transaction_received()

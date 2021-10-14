import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class TransactionPagHiper(models.Model):
    _inherit = "payment.transaction"

    def _send_payment_request(self):
        """ Override of payment to send a payment request to PagHiper.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_payment_request()
        if self.provider != "paghiper":
            return


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

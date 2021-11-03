import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class TransactionMercadoPago(models.Model):
    _inherit = "payment.transaction"

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider != "mercadopago":
            return res

        acquirer_id = self.env["payment.acquirer"].browse(
            processing_values["acquirer_id"]
        )
        res = acquirer_id._mercadopago_make_request(processing_values)

        return res

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        tx = super()._get_tx_from_feedback_data(provider, data)

        if provider != "mercadopago":
            return tx

        acquirer_reference = data.get("preference_id")
        tx = self.search([("acquirer_reference", "=", acquirer_reference)])
        return tx[0]

    def _process_feedback_data(self, data):
        super()._process_feedback_data(data)
        if self.provider != "mercadopago":
            return

        status = data.get("status")

        if status in ("approved", "authorized"):
            self._set_done()
        elif status in ("pending", "in_process"):
            self._set_pending()
        else:
            self._set_cancel()

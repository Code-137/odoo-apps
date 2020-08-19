from odoo import models, fields


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = "choose.delivery.carrier"

    packaging_id = fields.Many2one(
        comodel_name="product.packaging", string="Packages"
    )

    def _get_shipment_rate(self):
        return super(
            ChooseDeliveryCarrier,
            self.with_context(choose_delivery_carrier_id=self.id),
        )._get_shipment_rate()

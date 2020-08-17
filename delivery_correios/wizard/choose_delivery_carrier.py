from odoo import models, fields


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = "choose.delivery.carrier"

    package_ids = fields.Many2many(
        comodel_name="product.packaging", string="Packages"
    )

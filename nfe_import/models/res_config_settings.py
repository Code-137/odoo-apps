from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    product_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Sequência para código de produto",
        config_param="br_nfe_import.product_sequence",
    )

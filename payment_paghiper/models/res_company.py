from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    paghiper_api_key = fields.Char("PagHiper Api Key", size=100)

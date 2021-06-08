# License MIT (https://mit-license.org/)

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    juno_client_id = fields.Char(string="Juno Client Id")
    juno_client_secret = fields.Char(string="Juno Client Secret")
    juno_api_token = fields.Char(string="Juno API Token")
    juno_url_base = fields.Char(string="Juno URL")
    juno_environment = fields.Selection(
        string="Juno Environment",
        selection=[(1, "sandbox"), (2, "production")],
    )

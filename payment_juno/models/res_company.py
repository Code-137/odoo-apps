# License MIT (https://mit-license.org/)

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    juno_client_id = fields.Char(string="juno client id")
    juno_client_secret = fields.Char(string="juno client secret")
    juno_api_token = fields.Char(string="juno api token")
    juno_environment = fields.Selection(
        string="juno environment",
        selection=[(1, "sandbox"), (2, "production")],
    )

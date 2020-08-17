from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def get_company_logo(self):

        logo = self.with_context(
            {"bin_size": False}
        ).company_id.logo.decode("utf-8")

        return (
            '<img class="header-logo" style="max-height: 95px; width: 95px;"\
src="data:image/png;base64,'
            + logo
            + '"/>'
        )

    def get_nfe_number(self):
        return ""

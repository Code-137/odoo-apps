# License MIT (https://mit-license.org/)

from odoo.exceptions import ValidationError
from odoo import api, fields, models


class L10nBrPaymentMode(models.Model):
    _inherit = "l10n_br.payment.mode"

    juno_receivable = fields.Boolean(string="Juno?")

    @api.constrains("juno_receivable", "journal_id")
    def check_juno_validation(self):
        for item in self:
            if item.juno_receivable and not item.journal_id:
                raise ValidationError(
                    "Favor preencher o Diário para recebimento pelo Juno"
                )

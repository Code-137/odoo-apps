# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo.exceptions import ValidationError
from odoo import api, fields, models


class L10nBrPaymentMode(models.Model):
    _inherit = 'l10n_br.payment.mode'

    iugu_receivable = fields.Boolean(string="IUGU?")

    @api.constrains('iugu_receivable', 'journal_id')
    def check_iugu_validation(self):
        for item in self:
            if item.iugu_receivable and not item.journal_id:
                raise ValidationError(
                    'Favor preencher o Diário para recebimento pelo IUGU')
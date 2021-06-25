# License MIT (https://mit-license.org/)

import pprint
from odoo.exceptions import ValidationError, UserError
from odoo import api, models, _
from ..tools.juno_common import (
    create_juno_charge,
    juno_data_validation,
)


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    # Time for sending invoice data
    def juno_send_data(self):
        for invoice in self:
            for moveline in invoice.receivable_move_line_ids:
                if not moveline.payment_mode_id.juno_receivable:
                    continue

                juno_p = self.env["payment.acquirer"].search(
                    [("provider", "=", "juno")]
                )
                transaction = self.env["payment.transaction"].create(
                    {
                        "acquirer_id": juno_p.id,
                        "amount": moveline.amount_residual,
                        "currency_id": moveline.move_id.currency_id.id,
                        "partner_id": moveline.partner_id.id,
                        "type": "server2server",
                        "date_maturity": moveline.date_maturity,
                        "origin_move_line_id": moveline.id,
                        "invoice_ids": [(6, 0, self.ids)],
                    }
                )

                result = create_juno_charge(moveline)

                if not result.is_success:
                    raise UserError(pprint.pformat(result.errors))

                transaction.write(
                    {
                        "acquirer_reference": result.charge.id,
                        "transaction_url": result.charge.checkout_url,
                    }
                )

                moveline.write(
                    {
                        "juno_id": result.charge.id,
                        "juno_link": result.charge.checkout_url,
                        "juno_status": result.charge.status,
                    }
                )

    # Adding juno feature to Odoo Account Invoice method
    @api.multi
    def action_invoice_open(self):
        errors = juno_data_validation(self)

        if errors:
            raise ValidationError(errors)

        result = super(AccountInvoice, self).action_invoice_open()
        self.juno_send_data()
        return result

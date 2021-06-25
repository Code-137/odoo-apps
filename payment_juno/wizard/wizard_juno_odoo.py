# License MIT (https://mit-license.org/)

from odoo.exceptions import UserError
from odoo import api, fields, models
from ..tools.juno_common import cancel_juno_charge, create_juno_charge


class WizardInvoiceJuno(models.TransientModel):
    _name = "wizard.invoice.juno"

    juno_new_date = fields.Date(string="Inserir Novo Vencimento")
    juno_move_line_id = fields.Many2one("account.move.line", readonly=1)

    @api.multi
    def juno_action_invoice(self):
        if self.juno_new_date:
            if not self.juno_move_line_id:
                mvl_id = self.juno_move_line_id.browse(
                    self._context.get("active_id")
                )
            else:
                mvl_id = self.juno_move_line_id.browse(
                    self._context.get("active_id")
                )
            # In the case of invoice lines have reconciled
            if mvl_id.reconciled:
                raise UserError("Pagamento Reconciliado Anteriormente")
            else:
                # # parameter for list invoices in Juno
                # query_juno_inv = {'query': mvl_id.juno_id}
                result_cancel = cancel_juno_charge(mvl_id)
                result_create = create_juno_charge(
                    mvl_id, self.juno_new_date.strftime("%Y-%m-%d")
                )

                # Transaction registry
                mvl_id.write(
                    {
                        "date_maturity": self.juno_new_date,
                        "juno_id": result_create.charge.id,
                        "juno_link": result_create.charge.checkout_url,
                        "juno_statu": result_create.charge.status,
                    }
                )

                # Updating invoice data:
                mvl_id.invoice_id.write({"date_due": self.juno_new_date})

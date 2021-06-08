# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import iugu
from odoo.exceptions import UserError
from odoo import api, fields, models


class WizardInvoiceIugu(models.TransientModel):
    _name = 'wizard.invoice.iugu'

    iugu_new_date = fields.Date(string='Inserir Novo Vencimento')
    iugu_move_line_id = fields.Many2one('account.move.line', readonly=1)

    @api.multi
    def iugu_action_invoice(self):
        if self.iugu_new_date:
            if not self.iugu_move_line_id:
                mvl_id = self.iugu_move_line_id.browse(self._context.get('active_id'))
            else:
                mvl_id = self.iugu_move_line_id.browse(self._context.get('active_id'))
            # In the case of invoice lines have reconciled
            if mvl_id.reconciled:
                raise UserError('Pagamento Reconciliado Anteriormente')
            else:
                iugu_token = self.env.user.company_id.iugu_api_token
                iugu.config(token=iugu_token)
                iugu_invoice_api = iugu.Invoice()
                #
                # # parameter for list invoices in IUGU
                # query_iugu_inv = {'query': mvl_id.iugu_id}
                # # Listing invoices with iugu_subscription_id
                # data = iugu_invoice_api.list(query_iugu_inv)
                new_due_date_data = {
                    'due_date': self.iugu_new_date.strftime('%Y-%m-%d'),
                    'email': mvl_id.invoice_id.partner_id.email,
                }

                iugu_duplicate = iugu_invoice_api.duplicate
                iugu_data = iugu_duplicate(mvl_id.iugu_id, new_due_date_data)

                # Handling Errors
                if 'errors' in iugu_data:
                    msg = "\n".join(
                        ["IUGU: "] +
                        ["%s" % iugu_data['errors']])
                    raise UserError(msg)

                # Transaction registry
                mvl_id.write({
                    'date_maturity': self.iugu_new_date,
                    'iugu_id': iugu_data['id'],
                    'iugu_secure_payment_url': iugu_data['secure_url'],
                    'iugu_digitable_line': iugu_data['bank_slip']['digitable_line'],
                    'iugu_barcode_url': iugu_data['bank_slip']['barcode'],
                })

                # Updating invoice data:
                mvl_id.invoice_id.write({'date_due': self.iugu_new_date})
                # Updating sale order if exist
                subs_id =  mvl_id.invoice_id.subscription_id
                if subs_id:
                    sale_id = subs_id.sale_order_id
                    if sale_id:
                        sale_id.write({'iugu_secure_payment_url': iugu_data['secure_url']})

# License MIT (https://mit-license.org/)

import logging
import juno
import pprint
from datetime import date, datetime
from odoo.exceptions import UserError
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    juno_id = fields.Char(string="Juno ID", size=60)
    juno_status = fields.Char(string="Juno Status", default='pending')
    juno_link = fields.Char(string="URL de Pagamento", size=500)

    # TODO Constatar se existe juros na fatura após consulta no Juno 
    def juno_mark_paid(self):
        self.ensure_one()
        payment = self.env['account.payment']
        juno_journal = self.env['l10n_br.payment.mode'].search([('juno_receivable', '=', True)])[0]
        invoice = self.invoice_id
        juno_data = self.env.context.get('juno_data')
        # payment_date = juno_data['paid_at'][0:10] #Jove publish,
        payment_date = datetime.fromisoformat(juno_data['paid_at']).strftime('%Y-%m-%d')

        if juno_data:
            vals = {'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'currency_id': invoice.currency_id.id,
                    'payment_date': payment_date,
                    'partner_id': self.partner_id.id,
                    'amount': juno_data.get('total_paid_cents') / 100,
                    'destination_journal_id': False,
                    'payment_method_id': 1,
                    'partner_bank_account_id': False,
                    'journal_id': juno_journal.journal_id.id,
                    'communication': invoice.number + f' - juno_id: {juno_data["id"]}',
                    }

            payment_id = payment.create(vals)
            payment_id.update({'invoice_ids': invoice})
            payment_id.action_validate_invoice_payment()
            self.update({'juno_status': juno_data.get('status')})
            return True

        else:
            _logger.info('Juno sem pagamento automatico ==> %s', invoice.number)
            return 'No Automatic Payment from Juno'

    def juno_notify_late_payment(self):
        if self.invoice_id:
            self.invoice_id.message_post(
                body='Juno: Fatura atrasada')

    def juno_verify_payment(self):
        if self.juno_id:
            juno_token = self.env.user.company_id.juno_api_token
            juno.config(token=juno_token)
            juno_invoice_api = juno.Invoice()
            data = juno_invoice_api.search(self.juno_id)

            if "errors" in data:
                raise UserError(pprint.pformat(data['errors']))

            if data.get('status', '') == 'paid' and self.juno_status in ['pending', 'partially_paid']:
                # self.juno_status = data['status']
                ctx = self.env.context.copy()
                ctx.update({'juno_data': data})
                self.with_context(ctx).juno_mark_paid()

                # Adaptação ao módulo de assinaturas
                try:
                    inv = self.invoice_id
                    inv.webhook_call()
                except Exception as e:
                    _logger.error(pprint.pformat(e))

            else:
                self.juno_status = data['status']

        else:
            raise UserError('Parcela não enviada ao Juno')

    # cron job for verify payment
    @api.multi
    def cron_juno_verify_payment(self):
        company = self.env.company_id
        juno_client_id = company.juno_client_id
        juno_client_secret = company.juno_client_secret
        juno_token = company.juno_api_token
        juno_environment = company.juno_environment
        juno.init(
            client_id=juno_client_id,
            client_secret=juno_client_secret,
            resource_token=juno_token,
            sandbox=juno_environment,
        )
        #TODO Set the juno_status
        pending_lines = self.search([('juno_status', 'in', ['pending', 'partially_paid'])])

        #TODO Organize the query before to use the dueDateStart and dueDateEnd to get the charges
        for acc_move_line in pending_lines:
            data = juno_invoice_api.search(acc_move_line.juno_id)

            if acc_move_line.juno_id \
                    and data.get('status', '') == 'paid' \
                    and not acc_move_line.reconciled:
                # acc_move_line.update({'juno_status': data['status']})
                _logger.info('A Fatura %s será atualizada com o status: %s',
                             acc_move_line.ref, acc_move_line.juno_status)
                ctx = acc_move_line.env.context.copy()
                ctx.update({'juno_data': data})
                acc_move_line.with_context(ctx).juno_mark_paid()

            if 'errors' in data:
                _logger.error("Juno ERRORS ==> %s", pprint.pformat(data['errors']))

            else:
                continue

    def juno_cancel_acc_move_line(self):
        if not self.juno_id:
            raise UserError('Parcela não enviada ao Juno')
        juno_token = self.env.user.company_id.juno_api_token
        juno.config(token=juno_token)
        juno_invoice_api = juno.Invoice()
        juno_invoice_api.cancel(self.juno_id)
        self.juno_status = 'canceled'

    @api.multi
    def unlink(self):
        for line in self:
            if line.juno_id:
                juno_token = self.env.user.company_id.juno_api_token
                juno.config(token=juno_token)
                juno_invoice_api = juno.Invoice()
                juno_invoice_api.cancel(line.juno_id)
        return super(AccountMoveLine, self).unlink()

    def juno_open_wizard_invoice(self):
        return({
            'name': 'Nova Data de Vencimento Iugu',
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.invoice.juno',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_line_id': self.id,
            }
        })

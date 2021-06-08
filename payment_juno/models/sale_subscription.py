# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import iugu
import logging
import pprint
from dateutil.relativedelta import relativedelta
from datetime import datetime as dt
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from ..controllers.utils import iugu_get_invoice_api, iugu_get_subscription
_logger = logging.getLogger(__name__)


class SaleSubscription(models.Model):
    _inherit = 'sale.subscription'

    iugu_subs_identifier = fields.Char(string="ID Assinatura do IUGU")
    iugu_plan_identifier = fields.Char(string="ID Assinatura do IUGU")


    def iugu_subs_fetch_update_invoices(self):
        if self:
            for subs in self:
                iugu_subs_api = iugu_get_subscription(subs.company_id.iugu_api_token)
                iugu_return = iugu_subs_api.search(subs.iugu_subs_identifier).get('recent_invoices')
                if not 'errors' in iugu_return and len(iugu_return) > 0:
                    data = [inv for inv in iugu_return if inv.get('status') in ('pending', 'partially_paid', 'paid')]
                    inv_budget = self.env['account.invoice'].sudo().search([
                        ('subscription_id', '=', subs.id)]).filtered(lambda f: f.state not in (
                        'draft', 'cancel')).mapped('iugu_inv_identifier')
                    iugu_inv_for_odoo = [iugu_inv for iugu_inv in data if iugu_inv.get('id') not in inv_budget]
                    if iugu_inv_for_odoo:
                        for recurr_inv in iugu_inv_for_odoo:
                            ctx = subs.env.context.copy()
                            ctx.update({'iugu_data': [recurr_inv]})
                            invoice = subs.sudo().with_context(ctx)._recurring_create_invoice(automatic=True)
                            invoice = subs.iugu_fill_account_invoice_lines(recurr_inv, invoice)
                            ###### udpating next invoice date in subs ########
                            current_date = invoice.date_due
                            next_date = current_date
                            periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
                            invoicing_period = relativedelta(
                                **{periods[subs.recurring_rule_type]: subs.recurring_interval})
                            new_date = next_date + invoicing_period
                            subs.write({'recurring_next_date': new_date.strftime('%Y-%m-%d')})

                            return invoice
                    else:
                        _logger.info(f'Sem novas Faturas no IUGU ==> {subs.code}')
                else:
                    _logger.info(f'Sem novas Faturas no IUGU ==> {subs.code}')

    @api.multi
    def _recurring_create_invoice(self, automatic=False):
        iugu_invoice = self._context.get('iugu_data', [''])[0]
        if not iugu_invoice:
            iugu_return = self.iugu_list_invoice()
            iugu_invoice = iugu_return[0][0] if iugu_return[0] else None
            if not iugu_invoice:
                _logger.info(f'{self.code if self.code else "Sem Faturas "} ==> registradas no IUGU e no Odoo')
                return super()._recurring_create_invoice(automatic=automatic)
            invoice = None
            if 'id' in iugu_invoice:
                invoice =  super()._recurring_create_invoice(automatic=automatic)
                if self._context.get('iugu_data', [''])[0]:
                    iugu_invoice = self.iugu_get_invoice_data(self._context.get('iugu_data')[0].get('id'))

                invoice = self.iugu_fill_account_invoice_lines(iugu_invoice, invoice)

            else:
                _logger.exception('IUGU: sem invoice ==> %s', self.code)

            return invoice
        else:
            return super()._recurring_create_invoice(automatic=automatic)


    def iugu_list_invoice(self):
        iugu_invoice = self._context.get('iugu_data', [''])[0]
        iugu_data = []
        iugu_errors = []
        if not iugu_invoice:
            iugu_invoice_api = iugu_get_invoice_api(self.env.user.company_id.iugu_api_token)
            for subs in self:
                iugu_subs = self.iugu_subs_identifier
                # parameter for list invoices in IUGU
                query_iugu_inv = {'query': iugu_subs}
                # Listing invoices with iugu_subscription_id
                data = iugu_invoice_api.list(query_iugu_inv)
                iugu_odoo_invoices = self.env['account.invoice'].search([('iugu_subs_identifier', '=', iugu_subs)])
                iugu_inv_list_odoo = iugu_odoo_invoices.mapped('iugu_subs_identifier')

                if iugu_subs not in iugu_inv_list_odoo:
                    try:
                        _logger.info("IUGU LISTAGEM DE INVOICE NO SUBSCRIPTION ===> %s" % pprint.pformat(data.get('items', data)))
                        iugu_data.append(data['items'][0])
                    except IndexError as e:
                        _logger.error('Erro na consulta do IUGU ==> %s ==> Buscando segunda opção para consulta...',
                                      pprint.pformat(e))
                        iugu_subs_list = iugu.Subscription().search(iugu_subs).get('recent_invoices')
                        if iugu_subs_list:
                            data2 = iugu_invoice_api.search(iugu_subs_list[0].get('id'))
                            iugu_data.append({**data2['items'][0], **data2['bank_slip']})

                elif 'errors' in data or iugu_subs not in iugu_inv_list_odoo:
                    _logger.error('IUGU ERRORS ===> %s', pprint.pformat(data['errors']))
                    iugu_errors.append(data)
        return iugu_data, iugu_errors

    def _prepare_invoice(self):
        invoice = super()._prepare_invoice()
        data_iugu_invoice = iugu_inv = self._context.get('iugu_data', [''])[0]
        if not data_iugu_invoice:
            data_iugu_invoice = self.iugu_list_invoice()
            iugu_inv = data_iugu_invoice[0][0] if data_iugu_invoice else False
        if not iugu_inv:
            return invoice
        else:
            invoice.update({
                'iugu_inv_identifier': iugu_inv.get('id'),
                'iugu_subs_identifier': self.iugu_subs_identifier,
                'iugu_plan_identifier': self.iugu_plan_identifier,
                'date_due': iugu_inv.get('due_date'),
            })

        return invoice

    def iugu_get_invoice_data(self, iugu_invoice_id=None):
        if not iugu_invoice_id:
            raise ValidationError('Sem token do IUGU, entre em contato com o admin.')
        try:
            iugu_invoice_api = iugu_get_invoice_api(self.company_id.iugu_api_token)
            data2 = iugu_invoice_api.list({'query': iugu_invoice_id})
        except Exception as e:
            _logger.error(f'Erro no processamento da query no IUGU ==> {e}')
            return pprint.pformat(e)
        return data2.get('items')

    def iugu_fill_account_invoice_lines(self, iugu_data, invoice=None):

        for acc_move_line in invoice.receivable_move_line_ids:
            if not acc_move_line.payment_mode_id.iugu_receivable:
                continue
        data2 = self.iugu_get_invoice_data(iugu_data.get('id'))
        # data_invoice = data2[0]['created_at_iso'][0:10] #Jove publish
        data_invoice = dt.fromisoformat(data2[0]['created_at_iso']).strftime('%Y-%m-%d')

        merged_data = {**data2[0], **iugu_data}

        acc_move_line.write({
            'iugu_id': merged_data.get('id'),
            'iugu_secure_payment_url': merged_data.get('secure_url', ),
            'iugu_digitable_line': merged_data.get('digitable_line'),
            'iugu_barcode_url': merged_data.get('barcode'),
        })

        if merged_data.get('status') == 'paid':
            acc_move_line.iugu_verify_payment()

        invoice.update({'date_invoice': data_invoice})
        self.message_post(
            body=f'Fatura Gerada: {invoice.number}')

        return invoice

    def cron_iugu_create_recurring_invoice(self):
        elected_subs = self.sudo().search([('stage_id', 'not in', (4, 1))]).filtered(
            lambda subs: subs.recurring_next_date == (fields.Date.today() + relativedelta(days=6)))
        for subs in elected_subs:
            subs.iugu_subs_fetch_update_invoices()

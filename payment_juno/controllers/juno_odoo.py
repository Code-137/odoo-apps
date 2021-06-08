# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import juno
import logging
import pprint
from odoo import fields, http
from odoo.http import request, Response
from .utils import return_success, return_error_http, iugu_get_invoice_api

_logger = logging.getLogger(__name__)

# CONSTANTS
INVOICE_CHANGED = 'invoice.status_changed'
INVOICE_CREATED = 'invoice.created'
SUBSCRIPTION_CREATED = 'subscription.created'
INVOICE_DUE = 'invoice.due'
INVOICE_PAID = 'paid'
INVOICE_PENDING = 'pending'


class JunoController(http.Controller):

    @http.route('/juno/webhook', type='http', auth="none",
        methods=['GET', 'POST'], csrf=False)
    def juno_webhook(self, **post):
        ''' **post is like object {} with key values:
        'data[account_id]': 'Id da conta, no caso conta do Bradoo no IUGU',
        'data[id]': 'Id da Fatura do IUGU',
         'data[status]': status da fatura do Juno podendo ser-> ['paid', pending],
        'data[customer_email]': 'email do customer',
        'data[customer_name]': 'razao social ou nome do customer',
        'event': 'tipo de evento podendo ser: [subscription.renewed, invoice.status_changed etc]'''

        _logger.info(f'IUGU webhook arrived ==> {pprint.pformat(post)}')

        juno_id = post.get('data[id]')
        juno_status = post.get('data[status]')
        juno_event = post.get('event')
        juno_subs_id = post.get('data[subscription_id]')

        if juno_event == INVOICE_CHANGED and iugu_status == INVOICE_PAID:
            acc_move_line = request.env['account.move.line'].sudo().search(
                [('iugu_id', '=', iugu_id)])
            _logger.info('Atualizando A Fatura %s de %s para %s',
                         acc_move_line.ref, acc_move_line.iugu_status, iugu_status)

            # searching in iugu
            iugu_invoice = iugu_get_invoice_api(acc_move_line.company_id.iugu_api_token)
            iugu_data = iugu_invoice.search(iugu_id)

            if iugu_data.get('errors'):
                _logger.info('IUGU webhook Errors ==> %s', pprint.pformat(iugu_data.get('errors')))
                return return_error_http(f"IUGU: {iugu_data.get('errors')}")
            _logger.info(f'IUGU webhook payment announced ==> {pprint.pformat(iugu_data.get("items"))}')
            iugu_context = request.env.context.copy()
            iugu_context.update({'iugu_data': iugu_data})
            acc_move_line.with_context(iugu_context).iugu_mark_paid()

            # Adptação ao módulo de assinaturas
            try:
                inv = acc_move_line.invoice_id
                inv.webhook_call()
            except Exception as e:
                _logger.error(pprint.pformat(e))
            _logger.info(f'IUGU webhook processado: Fatura {acc_move_line.ref} marcada como paga no Odoo')

            return return_success('ok')

        elif iugu_event == INVOICE_DUE:
            acc_move_line = request.env['account.move.line'].sudo().search(
                [('iugu_id', '=', iugu_id)])
            acc_move_line.iugu_notify_late_payment()
            _logger.info('IUGU webhook ==> %s atrasada!', acc_move_line.ref)

            return return_success('ok')

        elif iugu_event == INVOICE_CREATED:
            if iugu_subs_id:
                subs_id = request.env['sale.subscription'].sudo().search([('iugu_subs_identifier', '=', iugu_subs_id)])

                if subs_id:
                    same_date = subs_id.create_date.date() == fields.Date.today()
                    _logger.info(f'{subs_id.code} date ==> {subs_id.create_date.date()} -- SAME DATE TODAY? ==> {same_date}')
                    if not same_date:
                        inv_subs = request.env['account.invoice'].sudo().search_read(
                            [('iugu_inv_identifier', '=', iugu_id), ('iugu_subs_identifier', '=', iugu_subs_id)],
                            ['subscription_id'])
                        if not inv_subs:
                            for subscription in subs_id:
                                subscription.iugu_subs_fetch_update_invoices()
                                return return_success('fatura sincronizada com sucesso')
                        else:
                            _logger.info(f'IUGU webhook: {subs_id.code} ==> fatura ja sincronizada anteriormente.')
                            return return_success(f'fatura {subs_id.code} ja sincronizada anteriormente')
            _logger.info(f'IUGU webhook: algo estranho aconteceu ==> {pprint.pformat(post)}')
            return return_success('ok')

        else:
            _logger.info('IUGU webhook without treatment for while ==> %s' % pprint.pformat(post))
            return return_success('ok')


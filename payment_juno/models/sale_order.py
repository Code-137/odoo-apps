# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import uuid
import iugu
import pprint
import re
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, tools
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def iugu_default_payment_mode(self):
        iugu_payment = self.env['l10n_br.payment.mode'].sudo().search([('iugu_receivable', '=', True)])
        return iugu_payment[0].id

    def iugu_default_term_date_sale(self):
        today = fields.Date.context_today(self)
        term_date = today + relativedelta(days=3)
        return term_date

    subscription_payment_term_id = fields.Many2one(
        string='Termo de Pagamento da Assinatura',
        comodel_name='account.payment.term',
        ondelete='set null',
        help='Termo de Pagamento para Assinatura'
    )

    iugu_secure_payment_url = fields.Char(
        string="Link de Cobrança",
        copy=False,
        size=500)

    payment_mode_id = fields.Many2one(
        string='Condições de Pagamento',
        comodel_name='l10n_br.payment.mode',
        default=iugu_default_payment_mode)

    data_vigencia = fields.Date(string='Vigência da Ordem', default=iugu_default_term_date_sale,
                           readonly=True, states={'draft': [('readonly', False)]}, index=True, copy=False,
                           help="Vigencia da Ordem de acordo com o Termo de Pagamento")

    @api.onchange('payment_term_id', 'date_order')
    def _onchange_payment_term_date_sale(self):
        date_order = self.date_order
        if not date_order:
            date_order = fields.Date.context_today(self)
        if self.payment_term_id:
            pterm = self.payment_term_id
            pterm_list = \
            pterm.with_context(currency_id=self.company_id.currency_id.id).compute(value=1, date_ref=date_order)[0]
            data_vigencia = max(line[0] for line in pterm_list)
            self.update({'data_vigencia': data_vigencia})
        elif self.data_vigencia and (date_order.date() > self.data_vigencia):
            self.data_vigencia = fields.Date.to_string(date_order.date())

    def iugu_create_plan(self):
        subscription = self.env['sale.subscription'].search([('sale_order_id', '=', self.id)])

        for subs in subscription:
            iugu_token = self.env.user.company_id.iugu_api_token
            iugu_url = self.env.user.company_id.iugu_url_base
            iugu.config(token=iugu_token)
            iugu_plan_api = iugu.Plan()

            subs.partner_id.iugu_synchronize()

            odoo_identifiers = [
                {'name': 'odoo_sale_order_' + str(self.id), 'identifier': self.name, 'value':  self.id},
                {'name': 'odoo_subscription_' + str(subs.id), 'identifier': subs.code, 'value': subs.id},
            ]

            vals = {
                'name': f"{subs.code}-{subs.partner_id.display_name}",
                'identifier': f"{subs.code}-{re.sub('[^0-9]', '', subs.partner_id.cnpj_cpf)}-"
                              f"{str(uuid.uuid4()).replace('-','').upper()[0:12]}",
                'interval': 1,  # A cada 1 mês
                'interval_type': 'months',
                'currency': self.currency_id.name.upper(),
                'payable_with': 'all',
                'value_cents': 000,
                'features': odoo_identifiers,
            }

            data = iugu_plan_api.create(vals)

            if "errors" in data:
                raise UserError(pprint.pformat(data['errors']))

            subs.write({'iugu_plan_identifier': data['identifier']})

        return True

    def iugu_create_subscription(self):
        subscription = self.env['sale.subscription'].search([('sale_order_id', '=', self.id)])

        for subs in subscription:
            iugu_token = self.env.user.company_id.iugu_api_token
            iugu_url = self.env.user.company_id.iugu_url_base
            iugu.config(token=iugu_token)
            iugu_subscription_api = iugu.Subscription()

            subs.partner_id.iugu_synchronize()

            subitems = [dict(description=f'[Assinatura-{subs.code}] ' + subs_orderlines.product_id.name,
                           quantity=int(subs_orderlines.quantity),
                           price_cents=int('{:.2f}'.format(subs_orderlines.price_unit).replace('.', '')),
                           recurrent='true')
                      for subs_orderlines in subs.recurring_invoice_line_ids]

            iugu_custom_variables = [
                {'name': self.name, 'value': self.name},
                {'name': subs.code, 'value': subs.code},
            ]
            vals = {
                'plan_identifier': subs.iugu_plan_identifier,
                'customer_id': subs.partner_id.iugu_id,
                'expires_at': subs.date_start.strftime('%d-%m-%Y'),  # A cada 1 mês
                'subitems': subitems,
                'custom_variables': iugu_custom_variables,
            }

            data = iugu_subscription_api.create(vals)

            if "errors" in data:
                raise UserError(pprint.pformat(data['errors']))

            subs.write({'iugu_subs_identifier': data['id']})

        return True

    @api.multi
    def _action_confirm(self):
        partner_iugu_validation = self._iugu_sale_validation()
        if partner_iugu_validation == 'ok':
            res = super()._action_confirm()
            iugu_payment_mode = self.payment_mode_id.iugu_receivable
            subscription = self.env['sale.subscription'].search([('sale_order_id', '=', self.id)])
            # subscription update
            subscription.update({'date_start': self.data_vigencia})
            if iugu_payment_mode and subscription:
                self.iugu_create_plan()
                self.iugu_create_subscription()
                for subs in subscription:
                    subs.write({'payment_mode_id': ''})
                    subs.recurring_invoice()
                    if subs.invoice_count == 1:
                        current_date = self.data_vigencia
                        next_date = current_date
                        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
                        invoicing_period = relativedelta(
                            **{periods[subs.recurring_rule_type]: subs.recurring_interval})
                        new_date = next_date + invoicing_period
                        subs.write({'recurring_next_date': new_date.strftime('%Y-%m-%d')})
                        invoice = self.env['account.invoice'].sudo().search([('subscription_id','=', subs.id)])
                        if invoice:
                            acc_move_line = invoice[0].receivable_move_line_ids
                            if acc_move_line:
                                self.write({'iugu_secure_payment_url': acc_move_line[0].iugu_secure_payment_url})
            return res
        else:
            raise UserError('Para prosseguir, corrigir os seguintes campos:\n' + '\n'.join(partner_iugu_validation))


    def _iugu_sale_validation(self):
        required_fields = []
        prod_constr = self.order_line.mapped('product_id').mapped('recurring_invoice')
        partner_number = self.partner_id.number
        partner_zip = self.partner_id.zip
        partner_email = self.partner_id.email
        iugu_ok_min_date = fields.Date.today() + relativedelta(days=3)
        iugu_ok_max_date = fields.Date.today() + relativedelta(days=8)  # no iugu a fatura deve ser em até 9 dias de hoje
        partner_cnpj_cpf = re.sub('[^0-9]', '', self.partner_id.commercial_partner_id.cnpj_cpf) \
            if self.partner_id.commercial_partner_id.cnpj_cpf else False
        if self.data_vigencia > iugu_ok_max_date:
            required_fields.append(f'- Data da Vigência da Ordem deve ser no '
                                   f'máximo até {iugu_ok_max_date.strftime("%d/%m/%Y")}')
        if self.data_vigencia < iugu_ok_min_date:
            required_fields.append(f'- Data da Vigência da Ordem deve ser no '
                                   f'mínimo até {iugu_ok_min_date.strftime("%d/%m/%Y")}')
        if not partner_cnpj_cpf or len(partner_cnpj_cpf) not in [11, 14]:
            required_fields.append('- Inserir CNPJ/CPF de Cliente Válido')
        if not partner_email or not tools.single_email_re.match(partner_email):
            required_fields.append('- Inserir Email de Cliente Válido')
        if not partner_zip or len(re.sub(r"\D", "", partner_zip)) != 8:
            required_fields.append('- Inserir CEP de Cliente Válido')
        if not partner_number:
            required_fields.append('- Inserir Número do Imóvel no Endereço do Cliente')
        if required_fields:
            return required_fields
        if prod_constr.count(True) and prod_constr.count(False):
            required_fields.append('- Produtos de Assinaturas misturados com Produtos de Não-Assinatura')
        if required_fields:
            return required_fields
        else:
            return 'ok'
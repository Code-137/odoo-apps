import json
import logging
import requests

from odoo import api, fields, models
from odoo.exceptions import UserError
from werkzeug import urls


_logger = logging.getLogger(__name__)


class PicPayAcquirer(models.Model):
    _inherit = "payment.acquirer"

    provider = fields.Selection(selection_add=[("picpay", "PicPay")])
    picpay_token = fields.Char("PicPay Token")
    picpay_seller_token = fields.Char("PicPay Seller Token")

    def picpay_form_generate_values(self, values):
        """ Função para gerar HTML POST do Iugu """
        base_url = (
            self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        )
        partner = self.env['res.partner'].browse(values.get('partner_id'))
        pic_vals = {
            'referenceId': values.get('reference'),
            'callbackUrl': '%s/picpay/notification' % base_url,
            'returnUrl': '%s/payment/process' % base_url,
            'value': values.get('amount'),
            'buyer': {
                'firstName': values.get('partner_first_name'),
                'lastName': values.get('partner_last_name'),
                'document': partner.l10n_br_cnpj_cpf,
                'email': values.get('billing_partner_email'),
                'phone': values.get('billing_partner_phone'),
            }
        }
        headers = {
            'Content-Type': 'application/json',
            'x-picpay-token': self.picpay_token,
        }
        url = 'https://appws.picpay.com/ecommerce/public/payments'
        response = requests.post(
            url, data=json.dumps(pic_vals), headers=headers
        )

        data = response.json()

        if not response.ok:
            raise UserError(data.get("message"))

        acquirer_reference = data.get("referenceId")
        payment_transaction_id = self.env['payment.transaction'].search(
            [("reference", "=", values['reference'])])

        payment_transaction_id.write({
            "acquirer_reference": acquirer_reference,
            "picpay_url": data['paymentUrl'],
        })

        return {
            "checkout_url": urls.url_join(
                base_url, "/picpay/checkout/redirect"),
            "secure_url": data['paymentUrl']
        }


class TransactionPicPay(models.Model):
    _inherit = "payment.transaction"

    picpay_url = fields.Char(string="Fatura PicPay", size=300)
    picpay_authorizarion = fields.Char(string="Autorização do Pagamento")

    @api.model
    def _picpay_form_get_tx_from_data(self, data):
        acquirer_reference = data.get("data[id]")
        tx = self.search([("acquirer_reference", "=", acquirer_reference)])
        return tx[0]

    def _picpay_form_validate(self, data):
        status = data.get("data[status]")

        if status in ('paid', 'partially_paid', 'authorized'):
            self._set_transaction_done()
            return True
        elif status == 'pending':
            self._set_transaction_pending()
            return True
        else:
            self._set_transaction_cancel()
            return False

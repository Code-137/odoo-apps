import logging
from odoo import http
from odoo.http import request
from werkzeug.utils import redirect

_logger = logging.getLogger(__name__)


class PicPayController(http.Controller):

    @http.route(
        '/picpay/notification/', type='http', auth="none",
        methods=['GET', 'POST'], csrf=False)
    def picpay_process_payment(self, **post):
        request.env['payment.transaction'].sudo().form_feedback(post, 'picpay')
        return "<status>OK</status>"

    @http.route(
        '/picpay/checkout/redirect', type='http',
        auth='none', methods=['GET', 'POST'])
    def picpay_checkout_redirect(self, **post):
        if 'secure_url' in post:
            return redirect(post['secure_url'])

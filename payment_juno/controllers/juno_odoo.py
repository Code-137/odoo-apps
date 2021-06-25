# License MIT (https://mit-license.org/)

import logging
import pprint
from odoo import http
from odoo.http import request
from .utils import return_success, return_error_http
from ..tools.juno_common import search_juno_charge

_logger = logging.getLogger(__name__)


class JunoController(http.Controller):
    @http.route(
        "/juno/webhook",
        type="http",
        auth="none",
        methods=["GET", "POST"],
        csrf=False,
    )
    def juno_webhook(self, **post):
        """**post is like object {} with key values:
        'data[account_id]': 'Id da conta, no caso conta do Bradoo no IUGU',
        'data[id]': 'Id da Fatura do IUGU',
         'data[status]': status da fatura do Juno podendo ser-> ['paid', pending],
        'data[customer_email]': 'email do customer',
        'data[customer_name]': 'razao social ou nome do customer',
        'event': 'tipo de evento podendo ser: [subscription.renewed, invoice.status_changed etc]"""

        _logger.info(f"Juno webhook arrived ==> {pprint.pformat(post)}")

        juno_id = post.get("data[entityId]")
        juno_status = post.get("data[atributtes][status]")
        juno_event = post.get("eventType")

        if juno_event == "CHARGE_STATUS_CHANGED" and juno_status == "PAID":
            acc_move_line = (
                request.env["account.move.line"]
                .sudo()
                .search([("juno_id", "=", juno_id)])
            )
            _logger.info(
                "Atualizando A Fatura %s de %s para %s",
                acc_move_line.ref,
                acc_move_line.juno_status,
                juno_status,
            )

            # searching in juno
            result = search_juno_charge(acc_move_line.juno_id)

            if not result.is_success:
                _logger.info(
                    "Juno webhook Errors => %s", pprint.pformat(result.errors)
                )

                return return_error_http(
                    result.status, f"JUNO: {pprint.pformat(result.errors)}"
                )

            _logger.info(
                f'IUGU webhook payment announced ==> {pprint.pformat(juno_data.get("items"))}'
            )

            acc_move_line.juno_mark_paid(result.charge)

            return return_success("ok")

        # TODO doing the process to get late payment
        # elif juno_event == INVOICE_DUE:
        # acc_move_line = (
        # request.env["account.move.line"]
        # .sudo()
        # .search([("juno_id", "=", juno_id)])
        # )
        # acc_move_line.juno_notify_late_payment()
        # _logger.info("IUGU webhook ==> %s atrasada!", acc_move_line.ref)

        # return return_success("ok")
        else:
            _logger.info(
                "IUGU webhook without treatment for while ==> %s"
                % pprint.pformat(post)
            )
            return return_success("ok")

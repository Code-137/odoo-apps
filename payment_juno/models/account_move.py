# License MIT (https://mit-license.org/)

import logging
import pprint
from datetime import date, datetime
from odoo.exceptions import UserError
from odoo import api, fields, models
from ..tools.juno_common import create_juno_charge, search_juno_charge, cancel_juno_charge, juno_data_validation 


_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    juno_id = fields.Char(string="Juno ID", size=60)
    juno_status = fields.Char(string="Juno Status", default="pending")
    juno_link = fields.Char(string="URL de Pagamento", size=500)

    # TODO Constatar se existe juros na fatura após consulta no Juno
    def juno_mark_paid(self, juno_charge):
        self.ensure_one()
        payment = self.env["account.payment"]
        juno_journal = self.env["l10n_br.payment.mode"].search(
            [("juno_receivable", "=", True)]
        )[0]
        invoice = self.invoice_id
        payment_date = juno_charge.due_date

        if juno_charge:
            vals = {
                "payment_type": "inbound",
                "partner_type": "customer",
                "currency_id": invoice.currency_id.id,
                "payment_date": payment_date,
                "partner_id": self.partner_id.id,
                "amount": juno_charge.amount,
                "destination_journal_id": False,
                "payment_method_id": 1,
                "partner_bank_account_id": False,
                "journal_id": juno_journal.journal_id.id,
                "communication": invoice.number
                + f' - juno_id: {juno_charge.id}',
            }

            payment_id = payment.create(vals)
            payment_id.update({"invoice_ids": invoice})
            payment_id.action_validate_invoice_payment()
            self.update({"juno_status": juno_charge.status})
            return True

        else:
            _logger.info(
                "Juno sem pagamento automatico ==> %s", invoice.number
            )
            return "No Automatic Payment from Juno"

    def juno_notify_late_payment(self):
        if self.invoice_id:
            self.invoice_id.message_post(body="Juno: Fatura atrasada")

    def juno_verify_payment(self):
        if self.juno_id:
            result = search_juno_charge(self)

            if not result.is_success:
                    raise UserError(pprint.pformat(result.errors))

            if result.charge.status == "PAID" and self.juno_status in [
                "ACTIVE",
            ]:
                self.juno_status = result.charge.status
                self.juno_mark_paid(result.charge)
            else:
                self.juno_status = result.charge.status
        else:
            raise UserError("Parcela não enviada ao Juno")

    # cron job for verify payment
    @api.multi
    def cron_juno_verify_payment(self):
        # TODO Set the juno_status
        pending_lines = self.search([("juno_status", "in", ["ACTIVE"])])

        # TODO Organize the query before to use the dueDateStart and dueDateEnd to get the charges
        for acc_move_line in pending_lines:
            result = search_juno_charge(acc_move_line)

            errors = ""
            if not result.is_success:
                for error in result.errors:
                    errors += error + " /n"

                _logger.error("Juno ERRORS => " + errors)

            if (
                acc_move_line.juno_id
                and result.charge.status == "PAID"
                and not acc_move_line.reconciled
            ):
                # acc_move_line.update({'juno_status': data['status']})
                _logger.info(
                    "A Fatura %s será atualizada com o status: %s",
                    acc_move_line.ref,
                    acc_move_line.juno_status,
                )
                ctx = acc_move_line.env.context.copy()
                ctx.update({"juno_data": result.charge})
                acc_move_line.juno_mark_paid(result.charge)
            else:
                continue

    def juno_cancel_acc_move_line(self):
        if not self.juno_id:
            raise UserError("Parcela não enviada ao Juno")

        result = cancel_juno_charge(self)

        if not result:
            self.juno_status = "CANCELED"
        else:
            raise UserError(pprint.pformat(result.errors))

    @api.multi
    def unlink(self):
        for line in self:
            if line.juno_id:
                result = cancel_juno_charge(line)

                if not result:
                    continue
                else:
                    raise UserError(pprint.pformat(result.errors))

        return super(AccountMoveLine, self).unlink()

    def juno_open_wizard_invoice(self):
        return {
            "name": "Nova Data de Vencimento Juno",
            "type": "ir.actions.act_window",
            "res_model": "wizard.invoice.juno",
            "view_type": "form",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_move_line_id": self.id,
            },
        }

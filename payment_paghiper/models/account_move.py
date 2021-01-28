# © 2019 Danimar Ribeiro
# Part of OdooNext. See LICENSE file for full copyright and licensing details.

import re
import json
import requests

from datetime import date
from odoo import models, fields
from odoo.exceptions import ValidationError, UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def validate_data_for_payment_gateway(self):
        errors = []
        for invoice in self:
            if not invoice.payment_journal_id.receive_by_paghiper:
                continue
            partner = invoice.partner_id.commercial_partner_id
            if not self.env.user.company_id.paghiper_api_key:
                errors.append("Configure o token de API")
            if partner.is_company and not partner.l10n_br_legal_name:
                errors.append("Destinatário - Razão Social")
            if not partner.street:
                errors.append("Destinatário / Endereço - Rua")
            if not partner.l10n_br_number:
                errors.append("Destinatário / Endereço - Número")
            if not partner.zip or len(re.sub(r"\D", "", partner.zip)) != 8:
                errors.append("Destinatário / Endereço - CEP")
            if not partner.state_id:
                errors.append(u"Destinatário / Endereço - Estado")
            if not partner.city_id:
                errors.append(u"Destinatário / Endereço - Município")
            if not partner.country_id:
                errors.append(u"Destinatário / Endereço - País")
        if len(errors) > 0:
            msg = "\n".join(
                ["Por favor corrija os erros antes de prosseguir"] + errors
            )
            raise ValidationError(msg)

    def send_information_to_paghiper(self):
        if not self.payment_journal_id.receive_by_paghiper:
            return

        base_url = (
            self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        )

        for moveline in self.receivable_move_line_ids:
            paghiper = self.env["payment.acquirer"].search(
                [("provider", "=", "paghiper")]
            )
            transaction = self.env["payment.transaction"].create(
                {
                    "acquirer_id": paghiper.id,
                    "amount": moveline.amount_residual,
                    "currency_id": moveline.move_id.currency_id.id,
                    "partner_id": moveline.partner_id.id,
                    "type": "server2server",
                    "date_maturity": moveline.date_maturity,
                    "origin_move_line_id": moveline.id,
                    "invoice_ids": [(6, 0, self.ids)],
                }
            )

            commercial_partner_id = self.partner_id.commercial_partner_id

            vals = {
                "days_due_date": (
                    moveline.date_maturity - fields.Date.today()
                ).days,
                "items": [
                    {
                        "description": "Fatura Ref: %s" % moveline.name,
                        "quantity": 1,
                        "price_cents": int(moveline.amount_residual * 100),
                    }
                ],
                "return_url": "%s/my/invoices/%s" % (base_url, self.id),
                "notification_url": "%s/paghiper/notificacao" % (base_url),
                "fines": True,
                "late_payment_fine": 2,
                "per_day_interest": True,
                "order_id": transaction.reference,
                "type_bank_slip": "boletoA4",
                "payer_name": commercial_partner_id.name,
                "payer_email": self.partner_id.email,
                "payer_cpf_cnpj": commercial_partner_id.l10n_br_cnpj_cpf,
                "payer_phone": commercial_partner_id.phone,
                "payer_street": commercial_partner_id.street or "",
                "payer_city": commercial_partner_id.city_id.name or "",
                "payer_number": commercial_partner_id.l10n_br_number or "",
                "payer_state": commercial_partner_id.state_id.l10n_br_ibge_code
                or "",
                "payer_complement": commercial_partner_id.street2 or "",
                "payer_zip_code": re.sub(
                    "[^0-9]", "", commercial_partner_id.zip or ""
                ),
            }

            url = "https://api.paghiper.com/transaction/create/"
            headers = {"content-type": "application/json"}
            payload = json.dumps(vals)
            response = requests.request(
                "POST", url, data=payload, headers=headers
            )

            data = response.json().get("create_request")

            if data.get("result") == "success":
                transaction.write(
                    {
                        "acquirer_reference": data["transaction_id"],
                        "transaction_url": data["bank_slip"]["url_slip"],
                    }
                )
            else:
                raise UserError(data.get("response_message"))

    def generate_transaction_for_receivables(self):
        for item in self:
            item.send_information_to_paghiper()

    def action_post(self):
        self.validate_data_for_payment_gateway()
        result = super(AccountMove, self).action_post()
        self.generate_transaction_for_receivables()
        return result


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _create_bank_tax_move_line(self, transaction_data):
        bank_taxes = transaction_data.get("taxes_paid_cents") / 100

        ref = "Taxa: %s" % self.name
        journal = self.move_id.payment_journal_id
        currency = journal.currency_id or journal.company_id.currency_id

        move = self.env["account.move"].create(
            {
                "name": "/",
                "journal_id": journal.id,
                "company_id": journal.company_id.id,
                "date": date.today(),
                "ref": ref,
                "currency_id": currency.id,
                "type": "entry",
            }
        )
        aml_obj = self.env["account.move.line"].with_context(
            check_move_validity=False
        )
        credit_aml_dict = {
            "name": ref,
            "move_id": move.id,
            "partner_id": self.partner_id.id,
            "debit": 0.0,
            "credit": bank_taxes,
            "account_id": journal.default_debit_account_id.id,
        }
        debit_aml_dict = {
            "name": ref,
            "move_id": move.id,
            "partner_id": self.partner_id.id,
            "debit": bank_taxes,
            "credit": 0.0,
            "account_id": journal.company_id.l10n_br_bankfee_account_id.id,
        }
        aml_obj.create(credit_aml_dict)
        aml_obj.create(debit_aml_dict)
        move.post()
        return move

    def action_mark_paid_move_line(self, transaction_data):
        self.ensure_one()
        ref = "Fatura Ref: %s" % self.name

        journal = self.move_id.payment_journal_id
        currency = journal.currency_id or journal.company_id.currency_id

        payment = (
            self.env["account.payment"]
            .sudo()
            .create(
                {
                    "bank_reference": self.iugu_id,
                    "communication": ref,
                    "journal_id": journal.id,
                    "company_id": journal.company_id.id,
                    "currency_id": currency.id,
                    "payment_type": "inbound",
                    "partner_type": "customer",
                    "amount": self.amount_residual,
                    "payment_date": date.today(),
                    "payment_method_id": journal.inbound_payment_method_ids[
                        0
                    ].id,
                    "invoice_ids": [(4, self.move_id.id, None)],
                }
            )
        )
        payment.post()

        self._create_bank_tax_move_line(transaction_data)

    def unlink(self):
        # TODO
        return super(AccountMoveLine, self).unlink()

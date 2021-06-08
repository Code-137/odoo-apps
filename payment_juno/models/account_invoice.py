# License MIT (https://mit-license.org/)

import juno
import pprint
import re
from odoo.exceptions import ValidationError, UserError
from odoo import api, fields, models, _


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.multi
    def juno_data_validation(self):
        # Handling Errors in validation
        errors = []
        for invoice in self:
            partner = invoice.partner_id.commercial_partner_id
            company = self.env.user.company_id
            if partner.is_company and not partner.legal_name:
                errors.append(_("Legal Name"))
            if not partner.cnpj_cpf:
                errors.append(_("CNPJ/CPF"))
            if not partner.zip or len(re.sub(r"\D", "", partner.zip)) != 8:
                errors.append(_("ZIP"))
            if not partner.street:
                errors.append(_("Street"))
            if not partner.number:
                errors.append(_("Address Number"))
            if not partner.city_id:
                errors.append(_("City"))
            if not partner.state_id:
                errors.append(_("State"))
            if not partner.email:
                errors.append(_("E-mail"))
            if not company.juno_client_id:
                errors.append(_("Juno Client Id"))
            if not company.juno_client_secret:
                errors.append(_("Juno Client Secret"))
            if not company.juno_api_token:
                errors.append(_("Juno API Token"))
        if len(errors) > 0:
            msg = "\n".join(
                [_("Please, before continue, fix the following errors: ")]
                + errors
            )
            raise ValidationError(msg)

    # Time for sending invoice data
    def juno_send_data(self):
        for invoice in self:
            company = self.env.user.company_id
            partner = invoice.partner_id
            juno_client_id = company.juno_client_id
            juno_client_secret = company.juno_client_secret
            juno_token = company.juno_api_token
            juno_url = company.juno_url_base
            juno_environment = company.juno_environment
            juno.init(
                client_id=juno_client_id,
                client_secret=juno_client_secret,
                resource_token=juno_token,
                sandbox=juno_environment,
            )

            for acc_move_line in invoice.receivable_move_line_ids:
                if not acc_move_line.payment_mode_id.juno_receivable:
                    continue

                references = [
                    [
                        dict(
                            description="["
                            + invoice.number
                            + "] "
                            + inv_line.product_id.name,
                            quantity=int(inv_line.quantity),
                            price_cents=int(
                                "{:.2f}".format(inv_line.price_unit).replace(
                                    ".", ""
                                )
                            ),
                        )
                        for inv_line in invoice.invoice_line_ids
                    ]
                ]

                vals = {
                    "email": invoice.partner_id.email,
                    "due_date": acc_move_line.date_maturity.strftime(
                        "%Y-%m-%d"
                    ),
                    "ensure_workday_due_date": True,
                    "items": items,
                    "return_url": "%s/my/invoices/%s" % (juno_url, invoice.id),
                    "notification_url": "%s/juno/webhook?id=%s"
                    % (juno_url, invoice.id),
                    "fines": True,
                    "late_payment_fine": 2,
                    "per_day_interest": True,
                    "customer_id": invoice.partner_id.juno_id,
                    "early_payment_discount": False,
                    "order_id": invoice.name,
                }

                charge = {
                    "description": invoice.number,
                    "amount": acc_move_line.amount,
                    "due_date": acc_move_line.date_maturity.strftime(
                        "%Y-%m-%d"
                    ),
                    # TODO Check how to get the delay fees
                    # "fine": "",
                    # "interest": "",
                    # TODO Check how to get the line discount
                    # "discountAmount": "",
                    # TODO Check if this is really necessary
                    # "paymentTypes": [],
                }

                billing = {
                    "name": partner.name,
                    "document": partner.cnpj_cpf,
                    "email": partner.email,
                    "address": {
                        "street": partner.street,
                        "number": partner.number,
                        "city": partner.city_id.name,
                        "state": partner.state_id.name,
                        "postCode": partner.zip,
                        # TODO Add settings to control this
                        # "notify": "",
                    },
                }

                data = {
                    "charge": charge,
                    "billing": billing,
                }

                response = juno.charge.create(data)

                #TODO Check this error 
                if "errors" in response:
                    raise UserError(pprint.pformat(data["errors"]))

                acc_move_line.write(
                    {
                        "juno_id": data["id"],
                        "juno_link": data["secure_url"],
                        "juno_status": ""
                    }
                )

    # Adding juno feature to Odoo Account Invoice method
    @api.multi
    def action_invoice_open(self):
        self.juno_data_validation()
        result = super(AccountInvoice, self).action_invoice_open()
        self.juno_send_data()
        return result

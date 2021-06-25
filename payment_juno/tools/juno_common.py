# License MIT (https://mit-license.org/)

import juno
import logging
import pprint
import re
from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def init_juno_client(company):
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
    return juno


def juno_data_validation(invoices):
    # Handling Errors in validation
    errors = []
    for invoice in invoices:
        partner = invoice.partner_id.commercial_partner_id
        company = invoice.company_id
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
            [_("Please, before continue, fix the following errors: ")] + errors
        )
        return msg


def create_juno_charge(account_move_line, new_due_date=None):
    company = account_move_line.company_id
    partner = account_move_line.invoice_id.partner_id
    invoice = account_move_line.invoice_id
    juno_client = init_juno_client(company)

    charge = {
        "pixKey": "",
        "pixIncludeImage": True,
        "description": invoice.number,
        "references": [invoice.number],
        "amount": account_move_line.amount_residual,
        "dueDate": new_due_date
        or account_move_line.date_maturity.strftime("%Y-%m-%d"),
        "maxOverdueDays": 0,
        "fine": 0,
        "interest": "0.00",
        "discountAmount": "0.00",
        "discountDays": -1,
        "paymentTypes": ["BOLETO", "CREDIT_CARD"],
    }

    billing = {
        "name": partner.name,
        "document": re.sub("[^0-9]", "", partner.cnpj_cpf),
        "email": partner.email,
        "address": {
            "street": partner.street,
            "number": partner.number,
            "complement": partner.street2 or "",
            "neighborhood": partner.district or "",
            "city": partner.city_id.name,
            "state": partner.state_id.code,
            "postCode": re.sub("[^0-9]", "", partner.zip),
        },
        "phone": partner.phone or "",
    }

    vals = {"charge": charge, "billing": billing}
    result = juno_client.charge.create(vals)

    if not result.is_success:
        raise UserError(pprint.pformat(result.errors))

    return result


def search_juno_charge(account_move_line):
    company = account_move_line.company_id
    juno_client = init_juno_client(company)
    result = juno_client.charge.find_by_id(account_move_line.juno_id)

    if not result.is_success:
        _logger.info(
            "Juno webhook Errors => %s", pprint.pformat(result.errors)
        )
        raise UserError(pprint.pformat(result.errors))

    return result


def cancel_juno_charge(account_move_line):
    company = account_move_line.company_id
    juno_client = init_juno_client(company)
    result = juno_client.charge.cancelation(account_move_line.juno_id)

    if not result:
        return result

    raise UserError(pprint.pformat(result.errors))

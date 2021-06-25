# License MIT (https://mit-license.org/)

import iugu
import pprint
import re
from odoo import api, fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    iugu_id = fields.Char(string="IUGU ID", size=60)

    @api.multi
    def iugu_synchronize(self):
        for partner in self:
            iugu_token = self.env.user.company_id.iugu_api_token
            iugu.config(token=iugu_token)

            iugu_customer_api = iugu.Customer()
            iugu_partner_id = partner.commercial_partner_id
            # TODO Validar telefone e inserir no vals
            vals = {
                'email': partner.email,
                'name': iugu_partner_id.legal_name or iugu_partner_id.name,
                'notes': iugu_partner_id.comment or '',
                'cpf_cnpj': iugu_partner_id.cnpj_cpf,
                'zip_code': re.sub('[^0-9]', '', iugu_partner_id.zip),
                'number': iugu_partner_id.number,
                'street': iugu_partner_id.street or '',
                'city': iugu_partner_id.city_id.name or '',
                'state': iugu_partner_id.state_id.code or '',
                'district': iugu_partner_id.district or '',
                'complement': iugu_partner_id.street2 or '',
            }
            if not partner.iugu_id:
                data = iugu_customer_api.create(vals)
                if "errors" in data:
                    raise UserError(pprint.pformat(data['errors']))
                partner.update({'iugu_id': data['id']})
            else:
                iugu_customer_api.change(partner.iugu_id, vals)

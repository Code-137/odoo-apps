from odoo import http
from odoo.http import request
from odoo.addons.website.controllers.main import Website


class Website(Website):
    @http.route("/", type="http", auth="public", website=True)
    def index(self, **kw):
        super(Website, self).index(**kw)
        vals = {}
        if kw.get("message_sent"):
            message = "Sua mensagem foi enviada com sucesso!"
            vals.update({"message": message})
        return request.render("code137_website.homepage", vals)


class Code137Controller(http.Controller):
    @http.route("/form-create-lead", type="http", auth="public", website=True)
    def form_create_lead(self, access_token=False, **kw):
        vals = {
            "name": kw.get("name"),
            "contact_name": kw.get("name"),
            "email_from": kw.get("mail"),
            "description": kw.get("description"),
        }
        partner = request.env["res.partner"].search(
            [("email", "=", kw.get("mail"))], limit=1
        )
        if partner:
            vals.update({"partner_id": partner.id})
        request.env["crm.lead"].sudo().create(vals)
        return request.redirect("/?message_sent=1#code137-contact")

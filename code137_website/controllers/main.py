from odoo import http
from odoo.http import request


class Code137Controller(http.Controller):
    @http.route(
        "/form-create-lead",
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def form_create_lead(self, access_token=False, **kw):
        vals = {
            "name": kw.get("name"),
            "email_from": kw.get("email_from"),
            "phone": kw.get("phone"),
        }
        partner = request.env["res.partner"].search(
            [("email", "=", kw.get("mail"))], limit=1
        )
        if partner:
            vals.update({"partner_id": partner.id})
        request.env["crm.lead"].sudo().create(vals)
        return request.redirect("/form-success")

    @http.route(
        "/form-success",
        type="http",
        auth="public",
        website=True,
        methods=["GET"],
    )
    def form_success(self):
        return request.render("code137_website.form_success_page", {})

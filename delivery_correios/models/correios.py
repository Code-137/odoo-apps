# © 2020 Danimar Ribeiro, Trustcode
# Part of Trustcode. See LICENSE file for full copyright and licensing details.

import re
import logging
import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
from lxml import etree
from datetime import datetime
from odoo import api, fields, models
from odoo.exceptions import UserError

from zeep.exceptions import Fault

_logger = logging.getLogger(__name__)


class CorreiosServicos(models.Model):
    _name = "delivery.correios.service"

    code = fields.Char(string="Código", size=20)
    identifier = fields.Char(string="Identificador", size=20)
    name = fields.Char(string="Descrição", size=70, required=True)
    delivery_id = fields.Many2one("delivery.carrier", string="Método entrega")
    chancela = fields.Binary(string="Chancela")
    ano_assinatura = fields.Char(string="Ano Assinatura")


class CorreiosPostagemPlp(models.Model):
    _name = "delivery.correios.postagem.plp"

    name = fields.Char(string="Descrição", size=20, required=True)
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.user.company_id.id,
    )
    state = fields.Selection(
        [("draft", "Rascunho"), ("done", "Enviado")],
        string="Status",
        default="draft",
    )
    delivery_id = fields.Many2one("delivery.carrier", string="Método entrega")
    total_value = fields.Float(string="Valor Total")
    sent_date = fields.Date(string="Data Envio")
    id_plp_correios = fields.Char(string="Id Plp Correios", size=30)
    postagem_ids = fields.One2many(
        "delivery.correios.postagem.objeto", "plp_id", string="Postagens"
    )

    def unlink(self):
        for item in self:
            if item.state == "done":
                raise UserError("Não é possível excluir uma PLP já enviada")
        return super(CorreiosPostagemPlp, self).unlink()

    def barcode_url(self):
        url = (
            '<img style="width:350px;height:40px;"\
src="/report/barcode/Code128/'
            + self.id_plp_correios
            + '" />'
        )
        return url

    @api.model
    def _get_post_services(self):
        services = {}
        for item in self.postagem_ids:
            serv = item.delivery_id.service_id

            if serv.id not in services:
                services[serv.id] = {}
                services[serv.id]["name"] = serv.name
                services[serv.id]["code"] = serv.code
                services[serv.id]["quantity"] = 0

            services[serv.id]["quantity"] += 1
        return services

    def get_plp_xml(self, **dados):
        path = os.path.dirname(os.path.abspath(__file__)).split("/")[0:-1]
        env = Environment(
            loader=FileSystemLoader(os.path.join("/", *path, "templates")),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
        )
        xml = env.get_template("fecha_plp_varios_servicos.xml").render(dados)
        parser = etree.XMLParser(
            remove_blank_text=True, encoding="ISO-8859-1"
        )
        elem = etree.XML(xml, parser=parser)
        xml = etree.tostring(elem)
        return xml

    def action_generate_voucher(self):
        dados = {
            "cartaoPostagem": self.delivery_id.cartao_postagem,
            "numero_contrato": self.delivery_id.num_contrato,
            "numero_diretoria": "36",
            "codigo_administrativo": self.delivery_id.cod_administrativo,
            "nome_remetente": self.company_id.l10n_br_legal_name,
            "logradouro_remetente": self.company_id.street,
            "numero_remetente": self.company_id.l10n_br_number,
            "complemento_remetente": self.company_id.street2 or "",
            "bairro_remetente": self.company_id.l10n_br_district,
            "cep_remetente": re.sub("[^0-9]", "", self.company_id.zip or ""),
            "cidade_remetente": self.company_id.city_id.name,
            "uf_remetente": self.company_id.state_id.code,
            "telefone_remetente": re.sub(
                "[^0-9]", "", self.company_id.phone or ""
            ),
            "email_remetente": self.company_id.email,
        }
        postagens = []
        etiquetas = []
        for item in self.postagem_ids:
            etiqueta = item.name[:10] + item.name[11:]
            etiquetas.append(etiqueta)
            partner = item.stock_move_id.picking_id.partner_id
            product = item.stock_move_id.product_id
            postagens.append(
                {
                    "numero_etiqueta": item.name,
                    "codigo_servico_postagem": item.delivery_id.service_id.code.strip(),
                    "peso": "%d" % (product.weight * 1000),
                    "nome_destinatario": partner.l10n_br_legal_name
                    or partner.name,
                    "telefone_destinatario": re.sub(
                        "[^0-9]", "", partner.phone or ""
                    ),
                    "celular_destinatario": re.sub(
                        "[^0-9]", "", partner.mobile or ""
                    ),
                    "email_destinatario": partner.email,
                    "logradouro_destinatario": partner.street,
                    "complemento_destinatario": partner.street2 or "",
                    "numero_end_destinatario": partner.l10n_br_number,
                    "bairro_destinatario": partner.l10n_br_district,
                    "cidade_destinatario": partner.city_id.name,
                    "uf_destinatario": partner.state_id.code,
                    "cep_destinatario": re.sub(
                        "[^0-9]", "", partner.zip or ""
                    ),
                    "descricao_objeto": item.stock_move_id.product_id.name,
                    "valor_a_cobrar": "0",
                    "valor_declarado": "0",
                    "tipo_objeto": "2",
                    "altura": "%d" % product.altura,
                    "largura": "%d" % product.largura,
                    "comprimento": "%d" % product.comprimento,
                    "diametro": "%d" % product.diametro,
                    "servicos_adicionais": ["019", "001"],
                }
            )
        dados["objetos"] = postagens

        xml_to_send = self.get_plp_xml(**dados)

        try:
            idPlpCorreios = self.delivery_id.get_correio_sigep().fecha_plp(
                xml_to_send,
                self.id,
                self.delivery_id.cartao_postagem,
                etiquetas,
            )
        except Fault as e:
            raise UserError(e.message)

        self.write(
            {
                "sent_date": datetime.now(),
                "state": "done",
                "id_plp_correios": idPlpCorreios,
            }
        )


class CorreiosPostagemObjeto(models.Model):
    _name = "delivery.correios.postagem.objeto"

    name = fields.Char(string="Descrição", size=20, required=True)
    delivery_id = fields.Many2one("delivery.carrier", string="Método entrega")
    stock_move_id = fields.Many2one("stock.move", string="Item Entrega")
    plp_id = fields.Many2one("delivery.correios.postagem.plp", "PLP")
    evento_ids = fields.One2many(
        "delivery.correios.postagem.eventos", "postagem_id", "Eventos"
    )


class CorreiosEventosObjeto(models.Model):
    _name = "delivery.correios.postagem.eventos"

    etiqueta = fields.Char(string="Etiqueta")
    postagem_id = fields.Many2one(
        "delivery.correios.postagem.objeto", "Postagem"
    )
    status = fields.Char(string="Status")
    data = fields.Date(string="Data")
    local = fields.Char(string="Local")
    descricao = fields.Char(string="Descrição")
    detalhe = fields.Char(string="Detalhe")

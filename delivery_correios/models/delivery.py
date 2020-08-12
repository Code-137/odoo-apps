# © 2020 Danimar Ribeiro, Trustcode
# Part of Trustcode. See LICENSE file for full copyright and licensing details.

import re
import logging
import zeep
from datetime import datetime
from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from pysigep.client import SOAPClient
except ImportError:
    _logger.warning("Cannot import pysigep")


def check_for_correio_error(method):
    if "mensagem_erro" in method:
        raise UserError(method["mensagem_erro"])
    elif "erro" in method:
        raise UserError(method["erro"])
    elif hasattr(method, "cServico") and int(method.cServico.Erro) != 0:
        raise UserError(method.cServico.MsgErro)


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    has_contract = fields.Boolean(string="Tem Contrato?")
    correio_login = fields.Char(string=u"Login Correios", size=30)
    correio_password = fields.Char(string=u"Senha do Correio", size=30)
    cod_administrativo = fields.Char(string=u"Código Administrativo", size=20)
    num_contrato = fields.Char(string=u"Número de Contrato", size=20)
    cartao_postagem = fields.Char(
        string=u"Número do cartão de Postagem", size=20
    )

    delivery_type = fields.Selection(
        selection_add=[("correios", u"Correios")]
    )
    # Type without contract
    service_type = fields.Selection(
        [
            ("04014", "Sedex"),
            ("04510", "PAC"),
            ("04782", "Sedex 12"),
            ("04790", "Sedex 10"),
            ("04804", "Sedex Hoje"),
        ],
        string="Tipo de Entrega",
        help="Tipo de entrega utilizado quando a empresa não possui contrato \
com o Correio",
    )
    # Type for those who have contract
    service_id = fields.Many2one(
        "delivery.correios.service", string="Serviço"
    )
    mao_propria = fields.Selection(
        [("S", "Sim"), ("N", "Não")], string="Entregar em Mão Própria"
    )
    valor_declarado = fields.Boolean("Valor Declarado")
    aviso_recebimento = fields.Selection(
        [("S", "Sim"), ("N", "Não")], string="Receber Aviso de Entrega"
    )
    ambiente = fields.Selection(
        [("1", "Homologação"), ("2", "Produção")],
        default="1",
        string="Ambiente",
    )

    def get_correio_soap_client(self):
        return SOAPClient(
            ambiente=int(self.ambiente),
            senha=self.correio_password,
            usuario=self.correio_login,
        )

    def action_get_correio_services(self):
        client = SOAPClient(
            ambiente=int(self.ambiente),
            senha=self.correio_password,
            usuario=self.correio_login,
        )
        result = client.busca_cliente(self.num_contrato, self.cartao_postagem)
        check_for_correio_error(result)
        servicos = result["contratos"][0]["cartoesPostagem"][0]["servicos"]
        ano_assinatura = result["contratos"][0]["dataVigenciaInicio"]
        for item in servicos:
            correio = self.env["delivery.correios.service"]
            item_correio = correio.search([("code", "=", item["codigo"])])
            chancela = item["servicoSigep"]["chancela"]

            if item_correio:
                item_correio.write(
                    {
                        "name": item["descricao"],
                        "chancela": chancela and chancela.get("chancela"),
                        "ano_assinatura": str(ano_assinatura)[:4],
                    }
                )
            else:
                correio.create(
                    {
                        "code": item["codigo"],
                        "identifier": item["id"],
                        "chancela": chancela and chancela.get("chancela"),
                        "name": item["descricao"],
                        "delivery_id": self.id,
                    }
                )

    def _get_normal_shipping_rate(self, order):
        origem = re.sub("[^0-9]", "", order.company_id.zip or "")
        destino = re.sub("[^0-9]", "", order.partner_shipping_id.zip or "")
        total = 0.0
        messages = []
        for line in order.order_line.filtered(lambda x: not x.is_delivery):

            params = {
                "numero_servico": self.service_type,
                "peso": str(line.product_id.weight),
                "comprimento": str(line.product_id.comprimento),
                "altura": str(line.product_id.altura),
                "largura": str(line.product_id.largura),
                "diametro": str(0),
                "valor_declarado": 0,
                "aviso_recebimento": False,
                "mao_propria": False,
                "formato": 1,
                "cep_origem": origem,
                "cep_destino": destino,
            }

            cliente = self.get_correio_soap_client()

            response = cliente.calcular_preco_prazo(**params)

            data = response.cServico[0]

            if data.Erro == "0":
                total += float(data.Valor.replace(",", "."))
            else:
                messages.append(
                    "{0} - {1}".format(line.product_id.name, data.MsgErro)
                )

        if len(messages) > 0:
            return {
                "success": False,
                "price": 12,
                "error_message": "\n".join(messages),
            }
        else:
            return {
                "success": True,
                "price": total,
                "warning_message": "Prazo de entrega: {} dias".format(
                    data.PrazoEntrega
                ),
            }

    def correios_rate_shipment(self, order):
        return self._get_normal_shipping_rate(order)

    def correios_send_shipping(self, pickings):
        """ Send the package to the service provider

        :param pickings: A recordset of pickings
        :return list: A list of dictionaries (one per picking) containing of
                    the form::
                         { 'exact_price': price,
                           'tracking_number': number }
        """
        client = self.get_correio_soap_client()

        plp = self.env["delivery.correios.postagem.plp"].search(
            [("state", "=", "draft")], limit=1
        )
        if not len(plp):
            name = "%s - %s" % (
                self.name,
                datetime.now().strftime("%d-%m-%Y"),
            )
            plp = self.env["delivery.correios.postagem.plp"].create(
                {
                    "name": name,
                    "state": "draft",
                    "delivery_id": self.id,
                    "total_value": 0,
                    "company_id": self.company_id.id,
                }
            )
        res = []
        for picking in pickings:
            cnpj_empresa = re.sub(
                "[^0-9]", "", picking.company_id.l10n_br_cnpj_cpf or ""
            )

            tags = []
            preco_soma = 0
            for pack in picking.move_line_ids_without_package:
                usuario_preco_prazo = {
                    "nCdEmpresa": self.cod_administrativo,
                    "sDsSenha": self.correio_password,
                    "nCdServico": self.service_id.code,
                    "sCepOrigem": pack.location_id.company_id.zip,
                    "sCepDestino": picking.partner_id.zip,
                    "nVlPeso": pack.product_id.weight,
                    "nVlComprimento": pack.product_id.comprimento,
                    "nVlAltura": pack.product_id.altura,
                    "nVlLargura": pack.product_id.largura,
                    "nVlDiametro": pack.product_id.diametro,
                    "nCdFormato": 1,
                    "sCdMaoPropria": self.mao_propria,
                    "nVlValorDeclarado": self.product_id.lst_price,
                    "sCdAvisoRecebimento": self.aviso_recebimento,
                }
                usuario_preco_prazo["ambiente"] = self.ambiente
                preco = 12  # Calcular o preco novamente
                preco_soma += preco * pack.product_qty

                etiqueta = client.solicita_etiquetas(
                    "C", cnpj_empresa, self.service_id.identifier, 1
                )
                if len(etiqueta) > 0:
                    digits = client.gera_digito_verificador_etiquetas(
                        etiqueta
                    )
                    etiqueta = etiqueta[0].replace(" ", str(digits[0]))
                else:
                    raise UserError("Nenhuma etiqueta recebida")

                pack.track_ref = etiqueta
                tags.append(etiqueta)
                self.env["delivery.correios.postagem.objeto"].create(
                    {
                        "name": etiqueta,
                        "stock_pack_id": pack.id,
                        "plp_id": plp.id,
                        "delivery_id": self.id,
                    }
                )
            tags = ";".join(tags)
            pickings.carrier_tracking_ref = tags
            res.append({"exact_price": preco_soma, "tracking_number": tags})
            plp.total_value = preco_soma
        return res

    def get_correio_eventos(self, picking):
        client = zeep.Client(
            "http://webservice.correios.com.br/service/rastro/Rastro.wsdl"
        )
        params = {
            "usuario": self.correio_login,
            "senha": self.correio_password,
            "tipo": "L",
            "resultado": "U",
            "lingua": 101,
            "objetos": picking.carrier_tracking_ref.replace(";", ""),
        }
        return client.service.buscaEventos(**params)

    def correios_get_tracking_link(self, pickings):
        """ Ask the tracking link to the service provider

        :param pickings: A recordset of pickings
        :return list: A list of string URLs, containing the tracking links
         for every picking
        """

        for picking in pickings:
            for pack in picking.move_line_ids_without_package:
                objetos = self.get_correio_eventos(picking)
                objetos = objetos.objeto
                for objeto in objetos:
                    if len(objeto.erro) > 0:
                        raise UserError(objeto.erro)
                    postagem = self.env[
                        "delivery.correios.postagem.objeto"
                    ].search([("stock_pack_id", "=", pack.id)], limit=1)
                    correio_evento = {
                        "etiqueta": objeto.numero,
                        "postagem_id": postagem.id,
                    }
                    if hasattr(objeto, "evento"):
                        for evento in objeto.evento:
                            correio_evento["status"] = evento.status
                            correio_evento["data"] = datetime.strptime(
                                str(evento.data), "%d/%m/%Y"
                            )
                            correio_evento["local"] = (
                                evento.local
                                + " - "
                                + str(evento.codigo)
                                + ", "
                                + evento.cidade
                                + "/"
                                + evento.uf
                            )
                            correio_evento["descricao"] = evento.descricao
                            correio_evento["detalhe"] = evento.detalhe
                    self.env["delivery.correios.postagem.eventos"].create(
                        correio_evento
                    )
        return [
            "/web#min=1&limit=80&view_type=list&model=delivery.\
correios.postagem.plp&action=396"
        ]

    def correios_cancel_shipment(self, picking):
        """ Cancel a shipment
        """
        refs = picking.carrier_tracking_ref.split(";")
        objects = self.env["delivery.correios.postagem.objeto"].search(
            [("name", "in", refs)]
        )
        client = self.get_correio_soap_client()
        for obj in objects:
            client.bloquear_objeto(obj.name, obj.plp_id.id)
        picking.write({"carrier_tracking_ref": "", "carrier_price": 0.0})

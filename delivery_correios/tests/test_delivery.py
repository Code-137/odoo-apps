# © 2020 Danimar Ribeiro, Trustcode
# Part of Trustcode. See LICENSE file for full copyright and licensing details.
# flake8: noqa

import os

from lxml import objectify
from mock import patch
from odoo.tests.common import TransactionCase

root = os.path.dirname(__file__)
xmls = os.path.join(root, "xmls")


class TestDeliveryCorreios(TransactionCase):
    def setUp(self):
        super(TestDeliveryCorreios, self).setUp()
        product_uom = {
            "name": "UOM",
            "category_id": self.env["uom.category"]
            .create({"name": "Unity"})
            .id,
            "uom_type": "reference",
            "active": True,
            "rounding": 0.00100,
        }
        self.product_uom = self.env["uom.uom"].create(product_uom)
        produto = {
            "name": "Produto 1",
            "weight": 10,
            "comprimento": 20,
            "altura": 20,
            "largura": 20,
            "list_price": 20,
            "uom_id": self.product_uom.id,
            "uom_po_id": self.product_uom.id,
        }
        self.produto = self.env["product.product"].create(produto)
        correio = {
            "name": "Correio",
            "correio_login": "sigep",
            "correio_password": "n5f9t8",
            "cod_administrativo": "08082650",
            "num_contrato": "9912208555",
            "cartao_postagem": "0057018901",
            "delivery_type": "correios",
            "mao_propria": "N",
            "valor_declarado": False,
            "aviso_recebimento": "N",
            "ambiente": "1",
            "product_id": self.produto.id,
        }
        self.delivery = self.env["delivery.carrier"].create(correio)
        self.servico = self.env["delivery.correios.service"].create(
            {
                "ano_assinatura": "2016",
                "name": "Serviço 1",
                "code": "40215",
                "identifier": "foo bar baz",
                "delivery_id": self.delivery.id,
            }
        )
        self.delivery.write(
            {
                "service_id": self.servico.id,
            }
        )
        partner = {
            "name": "Parceiro 1",
            "company_type": "person",
            "l10n_br_cnpj_cpf": "515.741.801-93",
            "zip": "27336-400",
        }
        self.partner = self.env["res.partner"].create(partner)
        self.company = self.env["res.company"].create(
            {
                "l10n_br_legal_name": "Nome Legal",
                "name": "Company 1",
                "l10n_br_cnpj_cpf": "1234567890123234",
            }
        )
        sale_order = {
            "partner_id": self.partner.id,
        }
        self.sale_order = self.env["sale.order"].create(sale_order)
        sale_order_line = {
            "product_id": self.produto.id,
            "product_uom_qty": 2,
            "product_uom": self.product_uom.id,
            "order_id": self.sale_order.id,
        }
        self.sale_order_line = self.env["sale.order.line"].create(
            sale_order_line
        )
        self.sale_order.write(
            {
                "order_line": [(4, self.sale_order_line.id, 0)],
            }
        )

    @patch(
        "odoo.addons.delivery_correios.models.delivery.DeliveryCarrier.correios_rate_shipment"
    )
    def test_correios_get_shipping_price_from_so(self, preco):
        calcular_preco_prazo = os.path.join(xmls, "calcular_preco_prazo.xml")
        with open(calcular_preco_prazo, "r") as correio_return_xml:
            preco.return_value = objectify.fromstring(
                correio_return_xml.read()
            )
        entrega = self.env["delivery.carrier"].create(
            {
                "name": "Metodo 1",
                "delivery_type": "correios",
                "margin": 0,
                "integration_level": "rate_and_ship",
                "correio_login": "sigep",
                "correio_password": "n5f9t8",
                "cod_administrativo": "08082650",
                "num_contrato": "9912208555",
                "cartao_postagem": "0057018901",
                "ambiente": "1",
                "product_id": self.produto.id,
            }
        )
        servico = self.env["delivery.correios.service"].create(
            {
                "ano_assinatura": "2016",
                "name": "Serviço 1",
                "code": "40215",
                "identifier": "foo bar baz",
                "delivery_id": entrega.id,
            }
        )
        entrega.write(
            {
                "service_id": servico.id,
            }
        )
        self.sale_order.write({"carrier_id": entrega.id})
        preco = entrega.correios_get_shipping_price_from_so(self.sale_order)
        self.assertEqual(preco[0], 42.00)

    @patch(
        "odoo.addons.delivery_correios.models.delivery.DeliveryCarrier.action_get_correio_services"
    )
    def test_action_get_correio_services(self, services):
        # mock servicos
        busca_cliente = os.path.join(xmls, "busca_cliente.xml")
        with open(busca_cliente, "r") as correio_return_xml:
            services.return_value = objectify.fromstring(
                correio_return_xml.read()
            )
        self.delivery.action_get_correio_services()
        servicos = self.env["delivery.correios.service"].search(
            [("code", "=", "40096")]
        )
        self.assertTrue(
            len(servicos) == 1, "Número de serviços: %d " % len(servicos)
        )

    @patch(
        "odoo.addons.delivery_correios.models.delivery.DeliveryCarrier.get_correio_eventos"
    )
    @patch(
        "odoo.addons.delivery_correios.models.delivery.DeliveryCarrier.correios_rate_shipment"
    )
    def test_correios_get_tracking_link(self, eventos, preco):
        get_eventos = os.path.join(xmls, "get_eventos.xml")
        calcular_preco_prazo = os.path.join(xmls, "calcular_preco_prazo.xml")
        with open(get_eventos, "r") as correios_eventos:
            eventos.return_value = objectify.fromstring(
                correios_eventos.read()
            )
        with open(calcular_preco_prazo, "r") as correio_return_xml:
            preco.return_value = objectify.fromstring(
                correio_return_xml.read()
            )
        move_line = [
            (
                0,
                0,
                {
                    "name": "Move 1",
                    "product_id": self.produto.id,
                    "product_uom_qty": 1.0,
                    "product_uom": self.product_uom.id,
                    "state": "draft",
                },
            )
        ]
        pack_operation = [
            (
                0,
                0,
                {
                    "qty_done": 0,
                    "location_id": 1,
                    "location_dest_id": 1,
                    "product_id": self.produto.id,
                },
            )
        ]
        picking = self.env["stock.picking"].create(
            {
                "name": "Picking 1",
                "partner_id": self.partner.id,
                "move_lines": move_line,
                "location_id": 1,
                "location_dest_id": 1,
                "picking_type_id": 1,
                "pack_operation_product_ids": pack_operation,
            }
        )
        entrega = self.env["delivery.carrier"].create(
            {
                "name": "Metodo 1",
                "delivery_type": "correios",
                "margin": 0,
                "integration_level": "rate_and_ship",
                "correio_login": "sigep",
                "correio_password": "n5f9t8",
                "cod_administrativo": "08082650",
                "num_contrato": "9912208555",
                "cartao_postagem": "0057018901",
                "ambiente": "1",
                "product_id": self.produto.id,
            }
        )
        servico = self.env["delivery.correios.service"].create(
            {
                "ano_assinatura": "2016",
                "name": "Serviço 1",
                "code": "40215",
                "identifier": "foo bar baz",
                "delivery_id": entrega.id,
            }
        )
        entrega.write(
            {
                "service_id": servico.id,
            }
        )
        self.sale_order.write({"carrier_id": entrega.id})
        tracks_link = entrega.correios_get_tracking_link(picking)
        evento = self.env["delivery.correios.postagem.eventos"].search([])
        self.assertEqual(1, len(evento))
        self.assertEqual(evento.etiqueta, u"JF598971235BR")
        self.assertEqual(evento.data, u"2014-03-18")
        self.assertEqual(evento.status, u"23")
        self.assertEqual(
            evento.local_origem, u"CTCE MACEIO - 57060971, MACEIO/AL"
        )
        self.assertFalse(evento.local_destino)
        self.assertEqual(
            tracks_link,
            [
                "/web#min=1&limit=80&view_type=list&model=delivery.correios.\
postagem.plp&action=396"
            ],
        )

    @patch(
        "odoo.addons.delivery_correios.models.delivery.DeliveryCarrier._get_correios_tracking_ref"
    )
    @patch(
        "odoo.addons.delivery_correios.models.delivery.DeliveryCarrier.correios_rate_shipment"
    )
    def test_correios_send_shipping(self, etiquetas, preco):
        calcular_preco_prazo = os.path.join(xmls, "calcular_preco_prazo.xml")
        with open(calcular_preco_prazo, "r") as correio_return_xml:
            preco.return_value = objectify.fromstring(
                correio_return_xml.read()
            )
        etiquetas.return_value = ["DL760237272BR"]
        move_line = [
            (
                0,
                0,
                {
                    "name": "Move 1",
                    "product_id": self.produto.id,
                    "product_uom_qty": 1.0,
                    "product_uom": self.product_uom.id,
                    "state": "draft",
                },
            )
        ]
        pack_operation = [
            (
                0,
                0,
                {
                    "qty_done": 0,
                    "product_qty": 1,
                    "location_id": 1,
                    "location_dest_id": 1,
                    "product_id": self.produto.id,
                },
            )
        ]
        picking = self.env["stock.picking"].create(
            {
                "name": "Picking 1",
                "partner_id": self.partner.id,
                "move_lines": move_line,
                "location_id": 1,
                "location_dest_id": 1,
                "picking_type_id": 1,
                "pack_operation_product_ids": pack_operation,
            }
        )
        entrega = self.env["delivery.carrier"].create(
            {
                "name": "Metodo 1",
                "delivery_type": "correios",
                "margin": 0,
                "integration_level": "rate_and_ship",
                "correio_login": "sigep",
                "correio_password": "n5f9t8",
                "cod_administrativo": "08082650",
                "num_contrato": "9912208555",
                "cartao_postagem": "0057018901",
                "ambiente": "1",
                "product_id": self.produto.id,
            }
        )
        servico = self.env["delivery.correios.service"].create(
            {
                "ano_assinatura": "2016",
                "name": "Serviço 1",
                "code": "40215",
                "identifier": "foo bar baz",
                "delivery_id": entrega.id,
            }
        )
        entrega.write(
            {
                "service_id": servico.id,
            }
        )
        self.sale_order.write({"carrier_id": entrega.id})
        send = entrega.correios_send_shipping(picking)
        self.assertTrue(len(send) == 1)
        exact_price = send[0]["exact_price"]
        track_ref = send[0]["tracking_number"]
        self.assertEqual(track_ref, "DL760237272BR")
        self.assertEqual(exact_price, 42)
        postagem = self.env["delivery.correios.postagem.objeto"].search([])
        self.assertEqual(1, len(postagem))
        self.assertEqual(postagem.name, "DL760237272BR")
        plp = self.env["delivery.correios.postagem.plp"].search([])
        self.assertEqual(1, len(plp))
        self.assertEqual(plp.state, "draft")
        self.assertEqual(plp.total_value, 42)

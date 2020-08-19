# © 2020 Danimar Ribeiro, Trustcode
# Part of Trustcode. See LICENSE file for full copyright and licensing details.

import re
import logging
import requests
import base64

from odoo import models

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_barcode_image(self, barcode_type, code, width, height):
        web_base_url = self.env["ir.config_parameter"].search(
            [("key", "=", "web.base.url")], limit=1
        )

        url = "{}/report/barcode/?type={}&value={}&width={}&height={}".format(
            web_base_url.value, barcode_type, code, width, height
        )

        response = requests.get(url)

        image = base64.b64encode(response.content)
        return image.decode("utf-8")

    def tracking_qrcode(self):
        origem = self.picking_id.company_id
        destino = self.picking_id.partner_id

        dados = {}

        dados["destino_cep"] = re.sub("[^0-9]", "", destino.zip or "")
        dados["destino_compl"] = re.sub(
            r"\D", "", destino.l10n_br_number or ""
        ).zfill(5)
        dados["origem_cep"] = re.sub("[^0-9]", "", origem.zip or "")
        dados["origem_compl"] = re.sub(
            r"\D", "", origem.l10n_br_number or ""
        ).zfill(5)
        validador_cep_dest = sum(
            [int(n) for n in re.sub(r"\D", "", destino.zip) or ""]
        )
        next_10 = validador_cep_dest
        while next_10 % 10 != 0:
            next_10 += 1
        dados["validador_cep_dest"] = next_10 - validador_cep_dest

        dados["idv"] = "51"

        dados["etiqueta"] = self.picking_id.carrier_tracking_ref

        transportadora = self.picking_id.carrier_id
        servicos_adicionais = ""
        servicos_adicionais += (
            "01" if transportadora.aviso_recebimento == "S" else "00"
        )
        servicos_adicionais += (
            "02" if transportadora.mao_propria == "S" else "00"
        )
        servicos_adicionais += (
            "19" if transportadora.valor_declarado else "00"
        )
        dados["servicos_adicionais"] = servicos_adicionais.ljust(12, "0")

        dados["cartao_postagem"] = transportadora.cartao_postagem.zfill(10)
        dados["codigo_servico"] = transportadora.service_id.code
        dados["agrupamento"] = "00"
        dados["num_logradouro"] = destino.l10n_br_number.zfill(5) or "0" * 5
        dados["compl_logradouro"] = "{:.20}".format(
            str(destino.street2 or "")
        ).zfill(20)
        dados["valor_declarado"] = (
            str(self.product_id * self.product_qty)
            .replace(".", "")
            .replace(",", "")
            .zfill(5)
            if transportadora.valor_declarado
            else "00000"
        )
        if destino.phone:
            telefone = (
                re.sub(r"\D", "", destino.phone).replace(" ", "").zfill(12)
            )
        elif destino.mobile:
            telefone = (
                re.sub(r"\D", "", destino.mobile).replace(" ", "").zfill(12)
            )
        else:
            telefone = "0" * 12
        dados["telefone"] = telefone
        dados["latitude"] = "-00.000000"
        dados["longitude"] = "-00.000000"
        dados["pipe"] = "|"
        dados["reserva"] = " " * 30
        code = "{destino_cep}{destino_compl}{origem_cep}{origem_compl}\
{validador_cep_dest}{idv}{etiqueta}{servicos_adicionais}{cartao_postagem}\
{codigo_servico}{agrupamento}{num_logradouro}{compl_logradouro}\
{valor_declarado}{telefone}{latitude}{longitude}{pipe}{reserva}".format(
            **dados
        )

        return self._get_barcode_image("QR", code, 95, 95)

    def tracking_barcode(self):
        return self._get_barcode_image(
            "Code128", self.picking_id.carrier_tracking_ref, 300, 70
        )

    def zip_dest_barcode(self):
        cep = re.sub("[^0-9]", "", self.picking_id.partner_id.zip or "")
        return self._get_barcode_image('Code128', cep, 200, 50)

    def get_chancela(self):

        chancela = self.with_context(
            {"bin_size": False}
        ).picking_id.carrier_id.service_id.chancela.decode("utf-8")

        return (
            '<img class="header-chancela" style="height: 75px; width: 75px;"\
src="data:image/png;base64,'
            + chancela
            + '"/>'
        )

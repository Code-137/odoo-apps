import re
import pytz
import base64

from . import focus_nfse

from odoo import models, fields
from odoo.exceptions import UserError


class Document(models.Model):
    _inherit = "l10n_br_fiscal.document"

    nfse_url = fields.Char(string="NFSe URL")
    partner_email = fields.Char(
        string="E-mail do Parceiro", related="partner_id.email"
    )

    def generate_dict_values(self):
        self.ensure_one()

        emissor = {
            "cnpj": re.sub("[^0-9]", "", self.company_cnpj_cpf or ""),
            "inscricao_municipal": self.company_inscr_mun,
            "codigo_municipio": "%s%s"
            % (
                self.company_id.state_id.ibge_code,
                self.company_id.city_id.ibge_code,
            ),
        }
        tomador = {
            "cnpj_cpf": re.sub("[^0-9]", "", self.partner_cnpj_cpf or ""),
            "inscricao_municipal": re.sub(
                "[^0-9]", "", self.partner_inscr_mun or ""
            ),
            "empresa": self.partner_is_company,
            "nome_fantasia": self.partner_name,
            "razao_social": self.partner_legal_name or self.partner_name,
            "telefone": re.sub("[^0-9]", "", self.partner_phone or ""),
            "email": self.partner_email,
            "endereco": {
                "logradouro": self.partner_street,
                "numero": self.partner_number,
                "bairro": self.partner_district,
                "complemento": self.partner_street2 or "",
                "cep": re.sub("[^0-9]", "", self.partner_zip or ""),
                "codigo_municipio": "%s%s"
                % (
                    self.partner_state_id.ibge_code,
                    self.partner_city_id.ibge_code,
                ),
                "uf": self.partner_state_id.code,
            },
        }
        if self.partner_is_company:
            tomador["cnpj"] = tomador["cnpj_cpf"]
        else:
            tomador["cpf"] = tomador["cnpj_cpf"]
        items = []
        for line in self.fiscal_line_ids:
            aliquota = line.issqn_percent / 100
            unitario = round(line.amount_total / line.quantity, 2)
            items.append(
                {
                    "name": line.product_id.name,
                    "cst_servico": "0",
                    "codigo_servico": line.service_type_id.code,
                    "cnae_servico": line.cnae_id.code,
                    "codigo_servico_municipio": line.city_taxation_code_id.code_unmasked,
                    "descricao_codigo_municipio": line.city_taxation_code_id.name,
                    "aliquota": aliquota,
                    "base_calculo": round(line.issqn_base, 2),
                    "valor_unitario": unitario,
                    "quantidade": int(line.quantity),
                    "valor_total": round(line.amount_total, 2),
                }
            )
        outra_cidade = self.company_id.city_id.id != self.partner_city_id.id
        outro_estado = self.company_id.state_id.id != self.partner_state_id.id
        outro_pais = (
            self.company_id.country_id.id != self.partner_country_id.id
        )

        data_emissao = self.document_date.astimezone(
            pytz.timezone(self.env.user.tz)
        )

        aliquota_iss = len(items) and items[0]["aliquota"] or 0

        return {
            "nfe_reference": self.id,
            "natureza_operacao": "1",
            "regime_especial_tributacao": self.taxation_special_regime,
            "optante_simples_nacional": True,
            "ambiente": self.nfse_environment,
            "prestador": emissor,
            "tomador": tomador,
            "numero": "%06d" % int(self.document_number),
            "outra_cidade": outra_cidade,
            "outro_estado": outro_estado,
            "outro_pais": outro_pais,
            # TODO Check this field
            "regime_tributario": "simples",
            "itens_servico": items,
            "data_emissao": data_emissao.strftime("%Y-%m-%d"),
            "serie": self.document_serie_id.code or "",
            "numero_rps": self.rps_number,
            "discriminacao": str(self.name[:2000] or ""),
            "valor_servico": round(self.amount_total, 2),
            "base_calculo": round(self.amount_issqn_base, 2)
            or round(self.amount_issqn_wh_base, 2),
            "valor_iss": round(self.amount_issqn_value, 2),
            "valor_iss_retido": round(self.amount_issqn_wh_value, 2),
            "valor_total": round(self.amount_total, 2),
            "valor_pis": round(self.amount_pis_value, 2)
            or round(self.amount_pis_wh_value, 2),
            "valor_pis_retido": round(self.amount_pis_wh_value, 2),
            "valor_cofins": round(self.amount_cofins_value, 2)
            or round(self.amount_cofins_wh_value, 2),
            "valor_cofins_retido": round(self.amount_cofins_wh_value, 2),
            "valor_inss": round(self.amount_inss_value, 2)
            or round(self.amount_inss_wh_value, 2),
            "valor_inss_retido": round(self.amount_inss_wh_value, 2),
            "valor_ir": round(self.amount_irpj_value, 2)
            or round(self.amount_irpj_wh_value, 2),
            "valor_ir_retido": round(self.amount_irpj_wh_value, 2),
            "valor_csll": round(self.amount_csll_value, 2)
            or round(self.amount_csll_wh_value, 2),
            "valor_csll_retido": round(self.amount_csll_wh_value, 2),
            "fonte_carga_tributaria": "IBPT",
            "aedf": self.company_id.l10n_br_aedf,
            "client_id": self.company_id.l10n_br_client_id,
            "client_secret": self.company_id.l10n_br_client_secret,
            "user_password": self.company_id.l10n_br_user_password,
            "observacoes": self.fiscal_additional_data,
            "servico": {
                "item_lista_servico": len(items)
                and items[0]["codigo_servico"]
                or "",
                "codigo_tributario_municipio": len(items)
                and items[0]["codigo_servico_municipio"]
                or "",
                "aliquota": abs(aliquota_iss),
                "iss_retido": False if aliquota_iss >= 0 else True,
                "valor_iss": round(self.amount_issqn_value, 2)
                if round(self.amount_issqn_value, 2) >= 0
                else 0,
                "valor_iss_retido": abs(round(self.amount_issqn_value, 2))
                if round(self.amount_issqn_value, 2) < 0
                else 0,
                "valor_inss": round(self.amount_inss_value, 2)
                or round(self.amount_inss_wh_value, 2),
                "valor_inss_retido": round(self.amount_inss_wh_value, 2),
                "valor_servicos": round(self.amount_total, 2),
                "discriminacao": self.fiscal_additional_data,
            },
        }

    def _eletronic_document_send(self):
        if self.document_type_id.code != "SE":
            return super(Document, self)._eletronic_document_send()
        doc_vals = self.generate_dict_values()
        response = focus_nfse.send_api(
            self.company_id.focus_nfse_token_acess,
            self.nfse_environment,
            doc_vals,
        )
        if response["code"] in (200, 201):
            vals = {
                "authorization_protocol": response["entity"]["protocolo_nfe"],
                "document_number": response["entity"]["numero_nfe"],
                "state_edoc": "autorizada",
                "status_code": "100",
                "status_name": "Nota emitida com sucesso!",
                "nfe_processada_name": "NFSe%08d.xml"
                % response["entity"]["numero_nfe"],
                "nfse_pdf_name": "NFSe%08d.pdf"
                % response["entity"]["numero_nfe"],
            }
            if response.get("xml", False):
                authorization_file = self.env["ir.attachment"].create(
                    {
                        "name": "NFSe%08d.xml"
                        % response["entity"]["numero_nfe"],
                        "res_model": self._name,
                        "res_id": self.id,
                        "datas": base64.encodestring(response["xml"]),
                        "mimetype": "application/xml",
                        "type": "binary",
                    }
                )
                vals["authorization_file_id"] = authorization_file.id
            if response.get("pdf", False):
                authorization_pdf = self.env["ir.attachment"].create(
                    {
                        "name": "NFSe%08d.pdf"
                        % response["entity"]["numero_nfe"],
                        "res_model": self._name,
                        "res_id": self.id,
                        "datas": base64.encodestring(response["pdf"]),
                        "mimetype": "application/xml",
                        "type": "binary",
                    }
                )
                vals["file_report_id"] = authorization_pdf.id
            if response.get("url_nfe", False):
                vals["nfse_url"] = response["url_nfe"]

            self.write(vals)
        elif response["code"] == "processing":
            self.write(
                {
                    "state": "enviada",
                }
            )
        else:
            raise UserError(
                "%s - %s" % (response["api_code"], response["message"])
            )

    def _document_cancel(self, justificative):
        if not self.nfse_url:
            return super(Document, self)._document_cancel(justificative)
        company = self.mapped("company_id").with_context({"bin_size": False})
        doc_values = {
            "aedf": company.l10n_br_aedf,
            "client_id": company.l10n_br_client_id,
            "client_secret": company.l10n_br_client_secret,
            "user_password": company.l10n_br_user_password,
            "ambiente": self.nfse_environment,
            "cnpj_cpf": re.sub("[^0-9]", "", self.company_cnpj_cpf),
            "inscricao_municipal": re.sub(
                "[^0-9]", "", self.company_inscr_mun
            ),
            "justificativa": "Emissao de nota fiscal errada",
            "numero": self.numero,
            "nfe_reference": str(self.id),
            "protocolo_nfe": self.protocolo_nfe,
            "codigo_municipio": "%s%s"
            % (
                self.company_state_id.l10n_br_ibge_code,
                self.company_city_id.l10n_br_ibge_code,
            ),
        }

        response = focus_nfse.cancel_api(
            company.focus_nfse_token_acess,
            doc_values["nfse_environment"],
            doc_values["nfe_reference"],
        )

        if response["code"] in (200, 201):
            vals = {
                "state_edoc": "cancelada",
                "status_code": response["code"],
                "status_name": response["message"],
            }
            if response.get("xml", False):
                # split na nfse antiga para adicionar o xml da nfe cancelada
                # [parte1 nfse] + [parte2 nfse]
                file = self.self.authorization_file_id
                split_nfe_processada = base64.decodebytes(file.datas).split(
                    b"</Nfse>"
                )
                # readicionar a tag nfse pq o mesmo é removido ao dar split
                split_nfe_processada[0] = split_nfe_processada[0] + b"</Nfse>"
                # [parte1 nfse] + [parte2 nfse] + [parte2 nfse]
                split_nfe_processada.append(split_nfe_processada[1])
                # [parte1 nfse] + [nfse cancelada] + [parte2 nfse]
                split_nfe_processada[1] = response["xml"]
                file.write(
                    {
                        "datas": base64.encodebytes(
                            b"".join(split_nfe_processada)
                        )
                    }
                )
            self.write(vals)
        else:
            raise UserError(
                "%s - %s" % (response["api_code"], response["message"])
            )

    def action_check_status_nfse(self):
        for edoc in self:
            response = focus_nfse.check_nfse_api(
                edoc.company_id.l10n_br_nfse_token_acess,
                edoc.nfse_environment,
                str(edoc.id),
            )
            if response["code"] in (200, 201):
                vals = {
                    "authorization_protocol": response["entity"][
                        "protocolo_nfe"
                    ],
                    "document_number": response["entity"]["numero_nfe"],
                    "state_edoc": "autorizada",
                    "status_code": "100",
                    "status_name": "Nota emitida com sucesso!",
                    "nfe_processada_name": "NFSe%08d.xml"
                    % response["entity"]["numero_nfe"],
                    "nfse_pdf_name": "NFSe%08d.pdf"
                    % response["entity"]["numero_nfe"],
                }
                if response.get("xml", False):
                    authorization_file = self.env["ir.attachment"].create(
                        {
                            "name": "NFSe%08d.xml"
                            % response["entity"]["numero_nfe"],
                            "res_model": edoc._name,
                            "res_id": edoc.id,
                            "datas": base64.encodestring(response["xml"]),
                            "mimetype": "application/xml",
                            "type": "binary",
                        }
                    )
                    vals["authorization_file_id"] = authorization_file.id
                if response.get("pdf", False):
                    authorization_pdf = self.env["ir.attachment"].create(
                        {
                            "name": "NFSe%08d.pdf"
                            % response["entity"]["numero_nfe"],
                            "res_model": edoc._name,
                            "res_id": edoc.id,
                            "datas": base64.encodestring(response["pdf"]),
                            "mimetype": "application/xml",
                            "type": "binary",
                        }
                    )
                    vals["file_report_id"] = authorization_pdf.id
                if response.get("url_nfe", False):
                    vals["nfse_url"] = response["url_nfe"]

                edoc.write(vals)

            elif response["code"] == 400:
                edoc.write(
                    {
                        "state_edoc": "error",
                        "status_code": response["api_code"],
                        "status_name": response["message"],
                    }
                )

    def cron_check_status_nfse(self):
        documents = self.search([("state", "=", "processing")], limit=100)
        documents.action_check_status_nfse()

{  # pylint: disable=C8101,C8103
    "name": "Importação de Documento Fiscal Eletronico",
    "version": "14.0.1.0.1",
    "category": "Account addons",
    "license": "AGPL-3",
    "author": "Code 137",
    "website": "http://www.code137.com.br",
    "description": """
        Implementa funcionalidade para importar XML da NFe.""",
    "contributors": [
        "Danimar Ribeiro <danimaribeiro@gmail.com>",
        "Felipe Paloschi <paloschi.eca@gmail.com>",
    ],
    "depends": ["sale", "l10n_br_nfe"],
    "data": [
        "data/payment_term.xml",
        "data/product.xml",
        "security/ir.model.access.csv",
        "views/res_config_settings.xml",
        "views/document.xml",
        "views/product_category.xml",
        "wizard/import_nfe.xml",
        "wizard/nfe_configuration.xml",
        "wizard/xml_import.xml",
    ],
}

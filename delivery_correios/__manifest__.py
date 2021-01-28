# pylint: skip-file
{
    "name": "Code137 - Correios",
    "summary": """Integração com os Correios \
    Módulo para gerar etiquetas de rastreamento de \
    encomendas""",
    "version": "13.0.1.0.0",
    "category": "MRP",
    "author": "Code 137",
    "license": "Other OSI approved licence",
    "website": "http://www.code137.com.br",
    "contributors": [
        "Danimar Ribeiro <danimaribeiro@gmail.com>",
        "Felipe Paloschi <paloschi.eca@gmail.com>",
    ],
    "depends": ["stock", "delivery"],
    "external_dependencies": {
        "python": ["zeep"],
    },
    "data": [
        "security/ir.model.access.csv",
        "views/correios.xml",
        "views/delivery_carrier.xml",
        "views/sale_order.xml",
        "views/product_template.xml",
        "views/stock_picking.xml",
        "wizard/choose_delivery_carrier.xml",
        "reports/shipping_label.xml",
        "reports/plp_report.xml",
    ],
    "application": True,
    "installable": True,
}

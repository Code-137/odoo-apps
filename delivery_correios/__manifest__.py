# © 2020 Danimar Ribeiro, Trustcode
# Part of Trustcode. See LICENSE file for full copyright and licensing details.

{
    'name': "Delivery Correios",
    'summary': """Integração com os Correios""",
    'description': """Módulo para gerar etiquetas de rastreamento de \
encomendas""",
    'version': '13.0.1.0.0',
    'category': 'MRP',
    'author': 'Code 137',
    'license': 'Other OSI approved licence',
    'website': 'http://www.code137.com.br',
    'contributors': [
        'Danimar Ribeiro <danimaribeiro@gmail.com>',
        'Felipe Paloschi <paloschi.eca@gmail.com>',
    ],
    'depends': [
        'stock', 'delivery'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/correios.xml',
        'views/delivery_carrier.xml',
        'views/sale_order.xml',
        'views/product_template.xml',
        'views/stock_picking.xml',
        'reports/shipping_label.xml',
        'reports/plp_report.xml',
    ],
    'application': True,
    'installable': True,
}

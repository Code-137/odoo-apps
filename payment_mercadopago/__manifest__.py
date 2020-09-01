{
    'name': "Método de Pagamento Mercado Pago",
    'summary': "Payment Acquirer: Mercado Pago",
    'description': """Mercado Pago payment gateway for Odoo.""",
    'author': "Code 137",
    'category': 'Accounting',
    'license': 'Other OSI approved licence',
    'version': '13.0.1.0.0',
    'depends': ['l10n_br_automated_payment', 'payment', 'sale'],
    'data': [
        'views/payment_views.xml',
        'views/mercadopago.xml',
        'data/mercadopago.xml',
    ],
    'application': True,
}

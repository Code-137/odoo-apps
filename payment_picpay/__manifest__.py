{
    'name': "Método de Pagamento PicPay",
    'summary': "Payment Acquirer: PicPay",
    'description': """PicPay payment gateway for Odoo.""",
    'author': "Danimar Ribeiro",
    'category': 'Accounting',
    'license': 'Other OSI approved licence',
    'version': '13.0.1.0.0',
    'depends': ['account', 'payment', 'sale'],
    'data': [
        'views/payment_views.xml',
        'views/picpay.xml',
        'data/picpay.xml',
    ],
    'application': True,
}

{
    'name': "Método de Pagamento PagHiper",
    'summary': "Payment Acquirer: PagHiper",
    'description': """PagHiper payment gateway for Odoo.""",
    'author': "Danimar Ribeiro",
    'category': 'Accounting',
    'license': 'Other OSI approved licence',
    'version': '13.0.1.0.0',
    'depends': ['l10n_br_automated_payment', 'payment', 'sale'],
    'data': [
        'views/payment_views.xml',
        'views/paghiper.xml',
        'views/account_journal.xml',
        'views/res_company.xml',
        'data/paghiper.xml',
    ],
    'application': True,
}

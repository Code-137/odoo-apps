{
    "name": "Método de Pagamento PicPay",
    "summary": "Payment Acquirer: PicPay",
    "description": """PicPay payment gateway for Odoo.""",
    "category": "Accounting",
    "license": "Other OSI approved licence",
    "version": "13.0.1.0.0",
    "author": "Code 137",
    "website": "http://www.code137.com.br",
    "contributors": ["Felipe Paloschi <paloschi.eca@gmail.com>"],
    "depends": ["account", "payment", "sale"],
    "data": [
        "views/payment_views.xml",
        "views/picpay.xml",
        "data/picpay.xml",
    ],
    "application": True,
}

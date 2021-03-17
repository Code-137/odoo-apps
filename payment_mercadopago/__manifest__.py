# pylint: skip-file
{
    "name": "Método de Pagamento Mercado Pago",
    "summary": "Payment Acquirer: Mercado Pago",
    "category": "Accounting",
    "version": "13.0.1.0.0",
    "author": "Code 137",
    "license": "Other OSI approved licence",
    "website": "http://www.code137.com.br",
    "contributors": [
        "Felipe Paloschi <paloschi.eca@gmail.com>",
    ],
    "depends": ["l10n_br_automated_payment", "payment", "sale"],
    "external_dependencies": {
        "python": ["mercadopago"],
    },
    "data": [
        "views/payment_views.xml",
        "views/mercadopago.xml",
        "data/mercadopago.xml",
    ],
    "application": True,
}

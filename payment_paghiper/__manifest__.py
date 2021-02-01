# pylint: skip-file
{
    "name": "Método de Pagamento PagHiper",
    "summary": "Payment Acquirer: PagHiper",
    "category": "Accounting",
    "version": "13.0.1.0.0",
    "author": "Code 137",
    "license": "Other OSI approved licence",
    "website": "http://www.code137.com.br",
    "contributors": [
        "Danimar Ribeiro <danimaribeiro@gmail.com>",
        "Felipe Paloschi <paloschi.eca@gmail.com>",
    ],
    "depends": ["l10n_br_automated_payment", "payment", "website_sale"],
    "data": [
        "views/payment_views.xml",
        "views/paghiper.xml",
        "views/account_journal.xml",
        "views/payment_portal_templates.xml",
        "data/paghiper.xml",
    ],
    "application": True,
}

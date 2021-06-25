# License MIT (https://mit-license.org/)

{
    "name": "Juno Integration for Odoo",
    "version": "12.0.0.1",
    "category": "Finance",
    "sequence": 5,
    "author": "Code 137",
    "license": "Other OSI approved licence",
    "summary": "Juno Integration for Odoo",
    "website": "www.code137.com.br",
    "contributors": [
        "Fábio Luna <fabio@code137.com.br>",
    ],
    "depends": [
        "br_account_payment",
        "sale_management",
    ],
    "external_dependencies": {
        "python": [
            "juno",
            "orjson",
        ],
    },
    "data": [
        "views/res_company.xml",
        "views/account_invoice.xml",
        "views/payment_mode.xml",
        "wizard/wizard_juno_odoo.xml",
        "data/juno_verify_payment_cron.xml",
    ],
    "application": True,
    "development_status": "Beta",
}

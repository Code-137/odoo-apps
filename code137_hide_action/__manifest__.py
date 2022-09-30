# pylint: skip-file
{
    "name": "Hide Action Button",
    "summary": """Hide 'Action' button from tree and form views""",
    "category": "Extra Tools",
    "license": "Other OSI approved licence",
    "version": "15.0.1.0.0",
    "author": "Code 137",
    "website": "https://www.code137.com.br",
    "contributors": [
        "Felipe Paloschi <paloschi.eca@gmail.com>",
    ],
    "depends": ["web"],
    "data": [
        "security/groups.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "code137_hide_action/static/src/js/hide_actions.js",
        ]
    },
    "images": ['static/description/00_action_button.png'],
}

# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_xmlids = [
    (
        "website_sale_stock.view_picking_form_inherit_website_sale_stock",
        "website_sale_stock.view_picking_form_inherit_website_sale",
    ),
]


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_xmlids(env.cr, _renamed_xmlids)

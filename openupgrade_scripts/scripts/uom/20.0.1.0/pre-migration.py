# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_xmlids = [
    ("uom.product_uom_form_action", "uom.uom_uom_action_list"),
    ("uom.product_uom_form_view", "uom.uom_uom_view_form"),
    ("uom.product_uom_tree_view", "uom.uom_uom_view_list"),
]


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_xmlids(env.cr, _renamed_xmlids)

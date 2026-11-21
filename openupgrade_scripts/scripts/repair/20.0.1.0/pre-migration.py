# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_fields = [
    ("repair.order", "repair_order", "product_uom", "uom_id"),
]

_copied_columns = {
    "repair_order": [
        ("state", None, None),
    ],
}


def repair_order_state(env):
    """
    State under_repair has been removed, such orders are confirmed now
    """
    openupgrade.map_values(
        env.cr,
        openupgrade.get_legacy_name("state"),
        "state",
        [("under_repair", "confirmed")],
        table="repair_order",
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_fields(env, _renamed_fields)
    openupgrade.copy_columns(env.cr, _copied_columns)
    repair_order_state(env)

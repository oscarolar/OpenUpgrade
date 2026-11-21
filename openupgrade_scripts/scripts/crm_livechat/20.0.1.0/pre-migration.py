# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_copied_columns = {
    "chatbot_script_step": [
        ("step_type", None, None),
    ],
}


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.copy_columns(env.cr, _copied_columns)
    openupgrade.map_values(
        env.cr,
        openupgrade.get_legacy_name("step_type"),
        "step_type",
        [("create_lead_and_forward", "create_lead")],
        table="chatbot_script_step",
    )

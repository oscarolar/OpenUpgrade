# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_added_columns = [
    ("calendar.event", "calendar_id", "many2one"),
    ("res.users", "primary_calendar_id", "many2one"),
]


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.add_columns(env, _added_columns)

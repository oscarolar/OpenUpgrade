# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "hr_expense", "20.0.2.1/noupdate_changes.xml")
    openupgrade.delete_records_safely_by_xml_id(
        env, ["hr_expense.seq_hr_expense_invoice"]
    )

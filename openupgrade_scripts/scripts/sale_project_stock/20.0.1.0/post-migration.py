# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def account_analytic_line_billable_type(env):
    has_sale_timesheets = openupgrade.column_exists(
        env.cr, "account_analytic_line", "project_id"
    ) and openupgrade.column_exists(
        env.cr, "account_analytic_line", "timesheet_invoice_type"
    )
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE account_analytic_line
        SET
            billable_type=CASE
                WHEN COALESCE(amount, 0) >= 0 AND COALESCE(unit_amount, 0) >= 0
                THEN '15_picking_entry_positive'
                ELSE '16_picking_entry_negative'
            END,
            category_report=CASE
                WHEN COALESCE(amount, 0) >= 0 AND COALESCE(unit_amount, 0) >= 0
                THEN 'revenues'
                ELSE 'costs'
            END
        WHERE category='picking_entry'
        {"AND project_id IS NULL" if has_sale_timesheets else ""}
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    account_analytic_line_billable_type(env)

# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def account_analytic_line_category(env):
    """
    Set the new category 'expense' on the analytic lines created from expenses, as 20
    does for new ones, and recompute their billable type
    """
    env.cr.execute(
        """
        UPDATE
            account_analytic_line
        SET
            category='expense'
        FROM
            account_move_line
        WHERE
            account_move_line.id=account_analytic_line.move_line_id
        AND
            account_move_line.expense_id IS NOT NULL
        AND
            account_analytic_line.category IS DISTINCT FROM 'expense'
        RETURNING
            account_analytic_line.id
        """
    )
    lines = env["account.analytic.line"].browse(
        [line_id for (line_id,) in env.cr.fetchall()]
    )
    lines.invalidate_recordset(["category"])
    env.add_to_compute(lines._fields["billable_type"], lines)
    lines.flush_recordset(["billable_type", "category_report"])


@openupgrade.migrate()
def migrate(env, version):
    account_analytic_line_category(env)

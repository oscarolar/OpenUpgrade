# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def account_analytic_line_product_id(env):
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_analytic_line
        SET product_id=sale_order_line.product_id
        FROM sale_order_line
        WHERE sale_order_line.id=account_analytic_line.so_line
        AND account_analytic_line.project_id IS NOT NULL
        AND sale_order_line.product_id IS NOT NULL
        AND account_analytic_line.product_id IS DISTINCT FROM
            sale_order_line.product_id
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "sale_timesheet", "20.0.1.0/noupdate_changes.xml")
    account_analytic_line_product_id(env)

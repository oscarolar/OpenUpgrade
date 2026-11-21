# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def sale_order_template_prepayment_percent(env):
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE sale_order_template
        SET prepayment_percent=0
        WHERE require_payment IS NOT TRUE
        AND COALESCE(prepayment_percent, 0) != 0
        """,
    )


def res_company_sale_order_template_id(env):
    env.cr.execute(
        """
        SELECT res_company.id, res_company.sale_order_template_id
        FROM res_company
        JOIN sale_order_template
            ON sale_order_template.id=res_company.sale_order_template_id
        """
    )
    IrDefault = env["ir.default"]
    for company_id, template_id in env.cr.fetchall():
        IrDefault.set(
            "sale.order",
            "sale_order_template_id",
            template_id,
            company_id=company_id,
        )


@openupgrade.migrate()
def migrate(env, version):
    sale_order_template_prepayment_percent(env)
    res_company_sale_order_template_id(env)

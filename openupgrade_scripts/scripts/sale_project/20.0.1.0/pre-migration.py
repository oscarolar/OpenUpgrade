# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_added_columns = [
    ("account.analytic.line", "billable_type", "selection"),
    ("account.analytic.line", "category_report", "selection"),
]


def _has_sale_timesheets(env):
    return openupgrade.column_exists(
        env.cr, "account_analytic_line", "project_id"
    ) and openupgrade.column_exists(
        env.cr, "account_analytic_line", "timesheet_invoice_type"
    )


def account_analytic_line_billable_type(env):
    has_sale_timesheets = _has_sale_timesheets(env)
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE account_analytic_line
        SET
            billable_type=computed.billable_type,
            category_report=CASE
                WHEN computed.billable_type IN (
                    '01_revenues_fixed',
                    '10_service_revenues',
                    '05_revenues_milestones',
                    '07_revenues_manual',
                    '19_materials',
                    '11_other_revenues'
                ) THEN 'revenues'
                ELSE 'costs'
            END
        FROM (
            SELECT
                line.id,
                CASE
                    WHEN COALESCE(line.amount, 0) >= 0
                    AND COALESCE(line.unit_amount, 0) >= 0
                    THEN CASE
                        WHEN product_template.type = 'consu'
                        THEN '19_materials'
                        WHEN product_template.type IS DISTINCT FROM 'service'
                        THEN '11_other_revenues'
                        WHEN product_template.invoice_policy = 'delivery'
                        THEN CASE product_template.service_type
                            WHEN 'timesheet' THEN '10_service_revenues'
                            WHEN 'milestones' THEN '05_revenues_milestones'
                            WHEN 'manual' THEN '07_revenues_manual'
                            ELSE '01_revenues_fixed'
                        END
                        WHEN product_template.invoice_policy = 'order'
                        THEN '01_revenues_fixed'
                        ELSE '11_other_revenues'
                    END
                    WHEN line.category = 'vendor_bill' THEN '12_vendor_bill'
                    ELSE '30_other_costs'
                END AS billable_type
            FROM account_analytic_line line
            LEFT JOIN sale_order_line
                ON sale_order_line.id=line.so_line
            LEFT JOIN product_product
                ON product_product.id=COALESCE(
                    line.product_id, sale_order_line.product_id
                )
            LEFT JOIN product_template
                ON product_template.id=product_product.product_tmpl_id
            {"WHERE line.project_id IS NULL" if has_sale_timesheets else ""}
        ) computed
        WHERE computed.id=account_analytic_line.id
        """,
    )
    if not has_sale_timesheets:
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_analytic_line
        SET
            billable_type=CASE timesheet_invoice_type
                WHEN 'billable_time' THEN '04_billable_time'
                WHEN 'timesheet_revenues' THEN '04_billable_time'
                WHEN 'billable_fixed' THEN '02_billable_fixed'
                WHEN 'billable_milestones' THEN '06_billable_milestones'
                WHEN 'billable_manual' THEN '08_billable_manual'
                WHEN 'non_billable' THEN '09_non_billable'
            END,
            category_report='costs'
        WHERE project_id IS NOT NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.add_columns(env, _added_columns)
    account_analytic_line_billable_type(env)

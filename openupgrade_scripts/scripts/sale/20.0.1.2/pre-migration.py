# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_fields = [
    (
        "product.template",
        "product_template",
        "expense_policy",
        "reinvoice_policy",
    ),
]

_added_columns = [
    ("sale.order", "document_tax_mode", "selection"),
    ("sale.order", "incoterm", "many2one"),
    ("sale.order", "incoterm_location", "char"),
    ("sale.order.line", "section_uom_id", "many2one"),
]

_deleted_xmlids = [
    "sale.action_accrued_revenue_entry_sale_order_line",
]


def account_analytic_line_reinvoice_move_id(env):
    if openupgrade.column_exists(
        env.cr, "account_analytic_line", "timesheet_invoice_id"
    ):
        openupgrade.rename_fields(
            env,
            [
                (
                    "account.analytic.line",
                    "account_analytic_line",
                    "timesheet_invoice_id",
                    "reinvoice_move_id",
                ),
            ],
        )


def product_template_sale_delay(env):
    if openupgrade.column_exists(env.cr, "product_template", "sale_delay"):
        openupgrade.rename_columns(
            env.cr, {"product_template": [("sale_delay", None)]}
        )


def product_template_invoice_policy(env):
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE product_template
        SET invoice_policy='order'
        WHERE invoice_policy IS NULL
        """,
    )


def sale_order_document_tax_mode(env):
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE sale_order
        SET document_tax_mode=COALESCE(
            root_company.account_price_include, 'tax_excluded'
        )
        FROM res_company
        JOIN res_company root_company
            ON root_company.id=split_part(res_company.parent_path, '/', 1)::integer
        WHERE res_company.id=sale_order.company_id
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE sale_order
        SET document_tax_mode='tax_excluded'
        WHERE document_tax_mode IS NULL
        """,
    )


def sale_order_delivery_status(env):
    if openupgrade.column_exists(env.cr, "sale_order", "delivery_status"):
        return
    openupgrade.add_columns(env, [("sale.order", "delivery_status", "selection")])
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE sale_order
        SET delivery_status=lines.delivery_status
        FROM (
            SELECT
                sale_order_line.order_id,
                CASE
                    WHEN bool_and(
                        CASE
                            WHEN COALESCE(sale_order_line.product_uom_qty, 0) > 0
                            THEN COALESCE(sale_order_line.qty_delivered, 0)
                                >= COALESCE(sale_order_line.product_uom_qty, 0)
                            ELSE COALESCE(sale_order_line.qty_delivered, 0)
                                <= COALESCE(sale_order_line.product_uom_qty, 0)
                        END
                    ) THEN 'full'
                    WHEN bool_or(COALESCE(sale_order_line.qty_delivered, 0) != 0)
                    THEN 'partial'
                    ELSE 'pending'
                END AS delivery_status
            FROM sale_order_line
            JOIN product_product
                ON product_product.id=sale_order_line.product_id
            JOIN product_template
                ON product_template.id=product_product.product_tmpl_id
            WHERE product_template.type='consu'
            GROUP BY sale_order_line.order_id
        ) lines
        WHERE lines.order_id=sale_order.id AND sale_order.state='sale'
        """,
    )


def sale_order_amount_unpaid(env):
    if openupgrade.column_exists(env.cr, "sale_order", "amount_unpaid"):
        return
    openupgrade.add_columns(
        env, [("sale.order", "amount_unpaid", "monetary", None, "sale_order")]
    )
    openupgrade.logged_query(
        env.cr,
        """
        WITH paid_transactions AS (
            SELECT
                sale_order_transaction_rel.sale_order_id,
                payment_transaction.id AS transaction_id,
                payment_transaction.amount
            FROM sale_order_transaction_rel
            JOIN payment_transaction
                ON payment_transaction.id=sale_order_transaction_rel.transaction_id
            WHERE payment_transaction.state IN ('authorized', 'done')
        ),
        paid AS (
            SELECT sale_order_id, SUM(amount) AS amount
            FROM paid_transactions
            GROUP BY sale_order_id
        ),
        offline_invoice_lines AS (
            SELECT DISTINCT
                sale_order_line.order_id,
                account_move_line.id,
                CASE
                    WHEN account_move_line.balance >= 0
                    THEN -ABS(COALESCE(account_move_line.price_total, 0))
                    ELSE ABS(COALESCE(account_move_line.price_total, 0))
                END AS amount
            FROM sale_order_line
            JOIN sale_order_line_invoice_rel
                ON sale_order_line_invoice_rel.order_line_id=sale_order_line.id
            JOIN account_move_line
                ON account_move_line.id=sale_order_line_invoice_rel.invoice_line_id
            WHERE account_move_line.parent_state IN ('draft', 'posted')
            AND NOT EXISTS (
                SELECT 1
                FROM paid_transactions
                JOIN account_invoice_transaction_rel
                    ON account_invoice_transaction_rel.transaction_id
                        =paid_transactions.transaction_id
                WHERE paid_transactions.sale_order_id=sale_order_line.order_id
                AND account_invoice_transaction_rel.invoice_id
                    =account_move_line.move_id
            )
        ),
        offline AS (
            SELECT order_id, SUM(amount) AS amount
            FROM offline_invoice_lines
            GROUP BY order_id
        )
        UPDATE sale_order
        SET amount_unpaid=GREATEST(
            COALESCE(sale_order.amount_total, 0)
            - COALESCE(paid.amount, 0)
            - COALESCE(offline.amount, 0),
            0
        )
        FROM sale_order sale_order2
        LEFT JOIN paid ON paid.sale_order_id=sale_order2.id
        LEFT JOIN offline ON offline.order_id=sale_order2.id
        WHERE sale_order2.id=sale_order.id
        """,
    )


def sale_order_line_section_fields(env):
    if not openupgrade.column_exists(env.cr, "sale_order_line", "section_qty"):
        openupgrade.logged_query(
            env.cr,
            "ALTER TABLE sale_order_line ADD COLUMN section_qty numeric DEFAULT 0",
        )
        openupgrade.logged_query(
            env.cr,
            "ALTER TABLE sale_order_line ALTER COLUMN section_qty DROP DEFAULT",
        )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE sale_order_line
        SET section_qty=1, section_uom_id=%s
        WHERE display_type IN ('line_section', 'line_subsection')
        """,
        (env.ref("uom.product_uom_unit").id,),
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_fields(env, _renamed_fields)
    account_analytic_line_reinvoice_move_id(env)
    product_template_sale_delay(env)
    product_template_invoice_policy(env)
    openupgrade.float_to_integer(env.cr, "sale_order_line", "customer_lead")
    openupgrade.add_columns(env, _added_columns)
    sale_order_document_tax_mode(env)
    sale_order_delivery_status(env)
    sale_order_amount_unpaid(env)
    sale_order_line_section_fields(env)
    openupgrade.delete_records_safely_by_xml_id(env, _deleted_xmlids)

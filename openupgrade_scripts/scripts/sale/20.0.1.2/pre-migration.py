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
        openupgrade.rename_columns(env.cr, {"product_template": [("sale_delay", None)]})


def product_template_invoice_policy(env):
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE product_template
        SET invoice_policy='order'
        WHERE invoice_policy IS NULL
        """,
    )


def sale_order_rewrite(env):
    """
    Rewrite sale_order once: document_tax_mode is filled from the root company's
    res.company#account_price_include, prepayment_percent is set to 0 on orders
    that did not require payment, as v20 only looks at prepayment_percent, and
    amount_unpaid (when pos_sale was not installed) starts at 0 and is computed
    afterwards for the orders that still have something to pay
    """
    env.cr.execute(
        """
        SELECT
            res_company.id,
            COALESCE(root_company.account_price_include, 'tax_excluded')
        FROM
            res_company
        JOIN
            res_company root_company
            ON root_company.id=split_part(res_company.parent_path, '/', 1)::integer
        """
    )
    tax_modes = env.cr.fetchall()
    tax_mode = "'tax_excluded'"
    if tax_modes:
        tax_mode = env.cr.mogrify(
            "CASE company_id {} ELSE 'tax_excluded' END".format(
                " ".join(["WHEN %s THEN %s"] * len(tax_modes))
            ),
            [value for row in tax_modes for value in row],
        ).decode()
    new_columns = [
        (column, column_type)
        for column, column_type in (
            ("document_tax_mode", "varchar"),
            ("amount_unpaid", "numeric"),
        )
        if not openupgrade.column_exists(env.cr, "sale_order", column)
    ]
    if new_columns:
        openupgrade.logged_query(
            env.cr,
            "ALTER TABLE sale_order {}".format(
                ", ".join(
                    f"ADD COLUMN {column} {column_type}"
                    for column, column_type in new_columns
                )
            ),
        )
    expressions = {
        "document_tax_mode": ("varchar", tax_mode),
        "amount_unpaid": ("numeric", "0"),
    }
    alterations = [
        f"ALTER COLUMN {column} TYPE {expressions[column][0]} "
        f"USING {expressions[column][1]}"
        for column, _column_type in new_columns
    ]
    if openupgrade.column_exists(env.cr, "sale_order", "require_payment"):
        alterations.append(
            """
            ALTER COLUMN prepayment_percent TYPE double precision USING CASE
                WHEN require_payment IS NOT TRUE
                    AND COALESCE(prepayment_percent, 0) != 0
                THEN 0
                ELSE prepayment_percent
            END
            """
        )
    if not alterations:
        return [column for column, _column_type in new_columns]
    openupgrade.logged_query(
        env.cr, "ALTER TABLE sale_order {}".format(", ".join(alterations))
    )
    return [column for column, _column_type in new_columns]


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
        ),
        unpaid AS (
            SELECT
                sale_order.id,
                GREATEST(
                    COALESCE(sale_order.amount_total, 0)
                    - COALESCE(paid.amount, 0)
                    - COALESCE(offline.amount, 0),
                    0
                ) AS amount
            FROM sale_order
            LEFT JOIN paid ON paid.sale_order_id=sale_order.id
            LEFT JOIN offline ON offline.order_id=sale_order.id
        )
        UPDATE sale_order
        SET amount_unpaid=unpaid.amount
        FROM unpaid
        WHERE unpaid.id=sale_order.id AND unpaid.amount != 0
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
    new_columns = sale_order_rewrite(env)
    sale_order_delivery_status(env)
    if "amount_unpaid" in new_columns:
        sale_order_amount_unpaid(env)
    sale_order_line_section_fields(env)
    openupgrade.delete_records_safely_by_xml_id(env, _deleted_xmlids)

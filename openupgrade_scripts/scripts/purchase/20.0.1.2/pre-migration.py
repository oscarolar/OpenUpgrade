# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_fields = [
    ("purchase.order.line", "purchase_order_line", "product_uom_id", "uom_id"),
]

_added_columns = [
    ("purchase.order", "incoterm_location", "char"),
    (
        "purchase.order.line",
        "non_deductible_tax",
        "float",
        None,
        "purchase_order_line",
        "double precision",
    ),
]


def purchase_order_document_tax_mode(env):
    """
    Fill purchase.order#document_tax_mode from the company's default, as the
    compute method does
    """
    if openupgrade.column_exists(env.cr, "purchase_order", "document_tax_mode"):
        return
    openupgrade.add_columns(env, [("purchase.order", "document_tax_mode", "selection")])
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            purchase_order
        SET
            document_tax_mode=COALESCE(
                root_company.account_price_include, 'tax_excluded'
            )
        FROM
            res_company
        JOIN
            res_company root_company
            ON root_company.id=split_part(res_company.parent_path, '/', 1)::integer
        WHERE
            res_company.id=purchase_order.company_id
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            purchase_order
        SET
            document_tax_mode='tax_excluded'
        WHERE
            document_tax_mode IS NULL
        """,
    )


def purchase_order_receipt_status(env):
    """
    purchase.order#receipt_status is defined in purchase now and computed from the
    received quantities when purchase_stock is not installed
    """
    openupgrade.update_module_moved_fields(
        env.cr,
        "purchase.order",
        ["incoterm_location", "receipt_status"],
        "purchase_stock",
        "purchase",
    )
    if openupgrade.column_exists(env.cr, "purchase_order", "receipt_status"):
        return
    openupgrade.add_columns(env, [("purchase.order", "receipt_status", "selection")])
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            purchase_order
        SET
            receipt_status=CASE
                WHEN order_lines.all_received THEN 'full'
                WHEN order_lines.any_received THEN 'partial'
                ELSE 'pending'
            END
        FROM (
            SELECT
                order_id,
                bool_and(
                    COALESCE(qty_received, 0) >= COALESCE(product_qty, 0)
                ) AS all_received,
                bool_or(COALESCE(qty_received, 0) != 0) AS any_received
            FROM
                purchase_order_line
            GROUP BY
                order_id
        ) order_lines
        WHERE
            order_lines.order_id=purchase_order.id
        AND
            purchase_order.state='purchase'
        """,
    )


def purchase_order_line_new_amounts(env):
    """
    Fill the new stored fields purchase.order.line#qty_to_invoice_raw and
    price_unit_product_uom with one rewrite of the table, then convert the price
    of the lines whose unit of measure is not the one of their product
    """
    columns = [
        column
        for column in ("qty_to_invoice_raw", "price_unit_product_uom")
        if not openupgrade.column_exists(env.cr, "purchase_order_line", column)
    ]
    if not columns:
        return
    openupgrade.logged_query(
        env.cr,
        "ALTER TABLE purchase_order_line {}".format(
            ", ".join(f"ADD COLUMN {column} numeric" for column in columns)
        ),
    )
    expressions = {
        "qty_to_invoice_raw": "COALESCE(product_qty, 0) - COALESCE(qty_invoiced, 0)",
        "price_unit_product_uom": """
            CASE
                WHEN display_type IS NOT NULL OR is_downpayment THEN 0
                ELSE price_unit::double precision
            END
        """,
    }
    openupgrade.logged_query(
        env.cr,
        "ALTER TABLE purchase_order_line {}".format(
            ", ".join(
                f"ALTER COLUMN {column} TYPE numeric USING {expressions[column]}"
                for column in columns
            )
        ),
    )
    if "price_unit_product_uom" not in columns:
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            purchase_order_line
        SET
            price_unit_product_uom=(
                purchase_order_line.price_unit * product_uom.factor / line_uom.factor
            )::double precision
        FROM
            uom_uom line_uom,
            product_product,
            product_template,
            uom_uom product_uom
        WHERE
            line_uom.id=purchase_order_line.uom_id
        AND
            product_product.id=purchase_order_line.product_id
        AND
            product_template.id=product_product.product_tmpl_id
        AND
            product_uom.id=product_template.uom_id
        AND
            line_uom.id != product_uom.id
        AND
            COALESCE(line_uom.factor, 0) != 0
        AND
            purchase_order_line.display_type IS NULL
        AND
            purchase_order_line.is_downpayment IS NOT TRUE
        """,
    )


def purchase_alternative(env):
    """
    Purchase alternatives have been split from purchase_requisition into the new
    module purchase_alternative: move model and fields there, and install the new
    module if the feature was in use.

    This needs to happen here because purchase_alternative can be loaded before
    purchase_requisition
    """
    if not openupgrade.table_exists(env.cr, "purchase_order_group"):
        return
    openupgrade.update_module_moved_models(
        env.cr, "purchase.order.group", "purchase_requisition", "purchase_alternative"
    )
    openupgrade.update_module_moved_fields(
        env.cr,
        "purchase.order",
        ["alternative_po_ids", "purchase_group_id"],
        "purchase_requisition",
        "purchase_alternative",
    )
    openupgrade.update_module_moved_fields(
        env.cr,
        "purchase.order.line",
        ["company_currency_id", "price_total_cc"],
        "purchase_requisition",
        "purchase_alternative",
    )
    openupgrade.logged_query(
        env.cr,
        """
        DROP TABLE IF EXISTS
            warning_purchase_order_rel, warning_purchase_order_alternative_rel
        """,
    )
    env.cr.execute(
        """
        SELECT
            EXISTS (
                SELECT 1 FROM purchase_order WHERE purchase_group_id IS NOT NULL
            )
            OR EXISTS (
                SELECT
                    1
                FROM
                    ir_model_data
                WHERE
                    ir_model_data.module='purchase_requisition'
                AND
                    ir_model_data.name='group_purchase_alternatives'
                AND
                    ir_model_data.model='res.groups'
                AND (
                    EXISTS (
                        SELECT 1 FROM res_groups_users_rel
                        WHERE gid=ir_model_data.res_id
                    )
                    OR EXISTS (
                        SELECT 1 FROM res_groups_implied_rel
                        WHERE hid=ir_model_data.res_id
                    )
                )
            )
        """
    )
    if env.cr.fetchone()[0]:
        env["ir.module.module"].search(
            [("name", "=", "purchase_alternative"), ("state", "=", "uninstalled")]
        ).button_install()


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_fields(env, _renamed_fields)
    openupgrade.add_columns(env, _added_columns)
    purchase_order_document_tax_mode(env)
    purchase_order_receipt_status(env)
    purchase_order_line_new_amounts(env)
    purchase_alternative(env)

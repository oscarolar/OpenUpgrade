# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_fields = [
    (
        "purchase.requisition.line",
        "purchase_requisition_line",
        "product_uom_id",
        "uom_id",
    ),
]


def purchase_requisition_line_price_subtotal(env):
    """
    Fill new stored computed field purchase.requisition.line#price_subtotal
    """
    if openupgrade.column_exists(
        env.cr, "purchase_requisition_line", "price_subtotal"
    ):
        return
    openupgrade.add_columns(
        env, [("purchase.requisition.line", "price_subtotal", "monetary")]
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            purchase_requisition_line
        SET
            price_subtotal=ROUND(
                (
                    COALESCE(purchase_requisition_line.product_qty, 0)
                    * COALESCE(purchase_requisition_line.price_unit, 0)
                )::numeric,
                COALESCE(res_currency.decimal_places, 2)
            )
        FROM
            purchase_requisition
        LEFT JOIN
            res_currency
        ON
            res_currency.id=purchase_requisition.currency_id
        WHERE
            purchase_requisition.id=purchase_requisition_line.requisition_id
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_fields(env, _renamed_fields)
    purchase_requisition_line_price_subtotal(env)

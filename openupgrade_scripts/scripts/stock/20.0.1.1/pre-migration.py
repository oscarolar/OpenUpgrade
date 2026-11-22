# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_fields = [
    ("stock.move", "stock_move", "product_uom", "uom_id"),
    ("stock.move", "stock_move", "location_final_id", "forecasted_location_id"),
    ("stock.move.line", "stock_move_line", "product_uom_id", "uom_id"),
    (
        "stock.picking.type",
        "stock_picking_type",
        "auto_show_reception_report",
        "auto_show_allocation_report",
    ),
]

_renamed_columns = {
    "stock_scrap_reason_tag": [("color", None)],
}

_product_label_formats = [
    ("dymo", "barcode_dymo"),
    ("2x7xprice", "barcode_2x7_price"),
    ("4x7xprice", "barcode_4x7_price"),
    ("4x12", "barcode_4x12"),
    ("4x12xprice", "barcode_4x12_price"),
    ("zpl", "barcode_zpl_normal"),
    ("zplxprice", "barcode_zpl_normal_price"),
]


def product_template_tracking(env):
    """
    product.template#tracking is not required anymore and lost its value 'none'
    """
    openupgrade.logged_query(
        env.cr, "ALTER TABLE product_template ALTER COLUMN tracking DROP NOT NULL"
    )
    openupgrade.logged_query(
        env.cr, "UPDATE product_template SET tracking=NULL WHERE tracking='none'"
    )


def res_company_horizon_days(env):
    """
    res.company#horizon_days is an integer now
    """
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE res_company
        ALTER COLUMN horizon_days TYPE integer USING round(horizon_days)::integer
        """,
    )


def stock_picking_type_product_label_format(env):
    """
    Map stock.picking.type#product_label_format to the composed keys of v20
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE stock_picking_type
        SET product_label_format = CASE product_label_format
            {}
            ELSE product_label_format END
        WHERE product_label_format IN %s
        """.format(
            " ".join(
                f"WHEN '{old}' THEN '{new}'" for old, new in _product_label_formats
            )
        ),
        (tuple(old for old, new in _product_label_formats),),
    )


def stock_picking_type_auto_show_allocation_report(env):
    """
    In v19 the reception report only showed up at validation if the group
    stock.group_reception_report was enabled. The group is gone in v20, so the flag
    is unset if the feature was disabled.
    """
    env.cr.execute(
        """
        SELECT 1
        FROM res_groups_implied_rel rel
        JOIN ir_model_data imd_user
            ON imd_user.model='res.groups' AND imd_user.res_id=rel.gid
            AND imd_user.module='base' AND imd_user.name='group_user'
        JOIN ir_model_data imd_report
            ON imd_report.model='res.groups' AND imd_report.res_id=rel.hid
            AND imd_report.module='stock'
            AND imd_report.name='group_reception_report'
        """
    )
    if env.cr.fetchone():
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE stock_picking_type
        SET auto_show_allocation_report=False
        WHERE auto_show_allocation_report
        """,
    )


def stock_picking_batch_installed(env):
    """
    Mark databases where stock_picking_batch (merged into stock) was installed, the
    post-migration enables the new group stock.group_stock_picking_batch for them
    """
    if not openupgrade.table_exists(env.cr, "stock_picking_batch"):
        return
    openupgrade.logged_query(
        env.cr,
        f"""
        ALTER TABLE stock_picking_batch
        ADD COLUMN IF NOT EXISTS {openupgrade.get_legacy_name("installed")} boolean
        """,
    )


def stock_move_quantity_product_uom(env):
    """
    Precompute the new stored field stock.move#quantity_product_uom
    """
    if openupgrade.column_exists(env.cr, "stock_move", "quantity_product_uom"):
        return
    openupgrade.logged_query(
        env.cr, "ALTER TABLE stock_move ADD COLUMN quantity_product_uom numeric"
    )
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE stock_move
        ALTER COLUMN quantity_product_uom TYPE numeric USING quantity
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE stock_move
        SET quantity_product_uom = round(
            (stock_move.quantity * move_uom.factor / product_uom.factor)::numeric,
            COALESCE((
                SELECT digits FROM decimal_precision WHERE name='Product Unit'
            ), 2)
        )
        FROM product_product
        JOIN product_template
            ON product_template.id=product_product.product_tmpl_id
        JOIN uom_uom product_uom ON product_uom.id=product_template.uom_id,
        uom_uom move_uom
        WHERE product_product.id=stock_move.product_id
        AND move_uom.id=stock_move.uom_id
        AND stock_move.uom_id != product_template.uom_id
        AND stock_move.quantity != 0
        """,
    )


def stock_picking_show_return(env):
    """
    Create stock.picking#show_return with its default beforehand, so that the ORM
    does not fill it with an UPDATE of every transfer
    """
    if openupgrade.column_exists(env.cr, "stock_picking", "show_return"):
        return
    openupgrade.add_columns(
        env, [("stock.picking", "show_return", "boolean", True, "stock_picking")]
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_fields(env, _renamed_fields)
    openupgrade.rename_columns(env.cr, _renamed_columns)
    product_template_tracking(env)
    res_company_horizon_days(env)
    stock_picking_type_product_label_format(env)
    stock_picking_type_auto_show_allocation_report(env)
    stock_picking_batch_installed(env)
    stock_move_quantity_product_uom(env)
    stock_picking_show_return(env)

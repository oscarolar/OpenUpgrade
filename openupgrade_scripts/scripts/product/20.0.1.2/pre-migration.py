# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_models = [
    ("website.base.unit", "product.base.unit"),
]

_renamed_tables = [
    ("website_base_unit", "product_base_unit"),
]

_renamed_fields = [
    ("product.supplierinfo", "product_supplierinfo", "product_uom_id", "uom_id"),
]

_renamed_xmlids = [
    ("website_sale.model_website_base_unit", "product.model_product_base_unit"),
    ("website_sale.base_unit_action", "product.base_unit_action"),
    ("website_sale.group_show_uom_price", "product.group_show_uom_price"),
]


def product_base_unit(env):
    """
    website.base.unit moved from website_sale to product as product.base.unit
    """
    if not openupgrade.table_exists(env.cr, "website_base_unit"):
        return
    openupgrade.rename_models(env.cr, _renamed_models)
    openupgrade.rename_tables(env.cr, _renamed_tables)


def product_pricelist_item_compute_price(env):
    """
    product.pricelist.item#compute_price lost 'percentage' and 'formula' in favour of
    'discount' and 'markup', which both apply price_discount with rounding, extra fee
    and margins. percent_price is gone, and rules of type 'percentage' ignored the
    other formula fields.
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE product_pricelist_item
        SET
            price_discount=COALESCE(percent_price, 0),
            price_round=0,
            price_surcharge=0,
            price_min_margin=0,
            price_max_margin=0,
            compute_price=CASE
                WHEN COALESCE(percent_price, 0) < 0 THEN 'markup' ELSE 'discount'
            END
        WHERE compute_price='percentage'
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE product_pricelist_item
        SET compute_price=CASE
            WHEN COALESCE(price_discount, 0) < 0
                OR (base='standard_price' AND COALESCE(price_discount, 0) <= 0)
            THEN 'markup' ELSE 'discount'
        END
        WHERE compute_price='formula'
        """,
    )


def product_pricelist_item_applied_on(env):
    """
    product.pricelist.item#applied_on is computed from the rule's category, template
    and variant now, be sure rules on variants have their template set
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE product_pricelist_item
        SET product_tmpl_id=product_product.product_tmpl_id
        FROM product_product
        WHERE product_product.id=product_pricelist_item.product_id
        AND product_pricelist_item.applied_on='0_product_variant'
        AND product_pricelist_item.product_tmpl_id IS DISTINCT FROM
            product_product.product_tmpl_id
        """,
    )


def product_product_lst_price(env):
    """
    Precompute the now stored product.product#lst_price
    """
    if openupgrade.column_exists(env.cr, "product_product", "lst_price"):
        return
    openupgrade.logged_query(
        env.cr, "ALTER TABLE product_product ADD COLUMN lst_price numeric"
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE product_product
        SET lst_price=COALESCE(product_template.list_price, 0) + COALESCE((
            SELECT SUM(ptav.price_extra)
            FROM product_variant_combination pvc
            JOIN product_template_attribute_value ptav
                ON ptav.id=pvc.product_template_attribute_value_id
            WHERE pvc.product_product_id=product_product.id
        ), 0)
        FROM product_template
        WHERE product_template.id=product_product.product_tmpl_id
        """,
    )


def product_template_barcode(env):
    """
    Precompute the now stored product.template#barcode
    """
    if openupgrade.column_exists(env.cr, "product_template", "barcode"):
        return
    openupgrade.logged_query(
        env.cr, "ALTER TABLE product_template ADD COLUMN barcode varchar"
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE product_template
        SET barcode=variant.barcode
        FROM (
            SELECT product_tmpl_id, MIN(barcode) AS barcode
            FROM product_product
            WHERE active
            GROUP BY product_tmpl_id
            HAVING COUNT(*) = 1
        ) variant
        WHERE variant.product_tmpl_id=product_template.id
        AND variant.barcode IS NOT NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    product_base_unit(env)
    openupgrade.rename_fields(env, _renamed_fields)
    openupgrade.rename_xmlids(env.cr, _renamed_xmlids)
    product_pricelist_item_compute_price(env)
    product_pricelist_item_applied_on(env)
    product_product_lst_price(env)
    product_template_barcode(env)

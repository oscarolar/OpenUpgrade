# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_fields = [
    ("website", "website", "contact_us_button_url", "contact_us_link_url"),
    ("website", "website", "prevent_zero_price_sale", "prevent_sale"),
    (
        "website",
        "website",
        "send_abandoned_cart_email",
        "send_abandoned_cart_followup",
    ),
]

_renamed_xmlids = [
    (
        "website_sale.ir_cron_send_availability_email",
        "website_sale.ir_cron_send_abandoned_email",
    ),
    (
        "website_sale_stock.ir_cron_send_availability_email",
        "website_sale.ir_cron_send_availability_email",
    ),
    (
        "website_sale.dynamic_snippet_newest_products_filter",
        "website_sale.dynamic_snippet_newest_arrivals_filter",
    ),
    (
        "website_sale.dynamic_filter_newest_products",
        "website_sale.dynamic_filter_newest_arrivals",
    ),
    (
        "website_sale.view_sales_order_filter_ecommerce_abondand",
        "website_sale.sale_order_abandoned_cart_search",
    ),
    ("website_payment.s_donation", "website_sale.s_donation"),
    ("website_payment.s_donation_button", "website_sale.s_donation_form"),
    ("website_payment.s_donation_000_scss", "website_sale.s_donation_000_scss"),
]

_renamed_view_keys = [
    ("website_payment.s_donation", "website_sale.s_donation"),
    ("website_payment.s_donation_button", "website_sale.s_donation_form"),
]

_merged_view_modules = ["website_sale_wishlist", "website_sale_comparison"]


def ir_ui_view_key(env):
    """
    Point the key of the qweb views (including the website specific copies) that
    moved to website_sale to their new xmlid
    """
    for old_key, new_key in _renamed_view_keys:
        openupgrade.logged_query(
            env.cr,
            "UPDATE ir_ui_view SET key=%s WHERE key=%s",
            (new_key, old_key),
        )
    for module in _merged_view_modules:
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE ir_ui_view
            SET key='website_sale.' || substr(key, %(length)s)
            WHERE
                left(key, %(prefix_length)s)=%(prefix)s
            AND
                NOT EXISTS (
                    SELECT 1 FROM ir_ui_view other_view
                    WHERE
                        other_view.key='website_sale.' || substr(
                            ir_ui_view.key, %(length)s
                        )
                    AND
                        other_view.website_id IS NOT DISTINCT FROM
                        ir_ui_view.website_id
                )
            """,
            {
                "prefix": f"{module}.",
                "prefix_length": len(module) + 1,
                "length": len(module) + 2,
            },
        )


def product_document_attached_on_sale(env):
    """
    product.document#shown_on_product_page became a value of
    product.document#attached_on_sale
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE product_document
        SET attached_on_sale='shown_on_product_page'
        WHERE
            shown_on_product_page
        AND
            attached_on_sale IN ('hidden', 'quotation', 'sale_order')
        """,
    )


def product_image_attribute_value_ids(env):
    """
    Variant images (product.image#product_variant_id) are now template images
    restricted to attribute values: link them to the template and to the attribute
    values of their variant, and fill product.product#variant_image_ids
    """
    openupgrade.add_columns(
        env, [("product.image", "has_attribute_value", "boolean", False)]
    )
    for table, column1, column2 in (
        (
            "product_image_attribute_value_rel",
            "product_image_id",
            "product_template_attribute_value_id",
        ),
        ("product_product_image_rel", "product_product_id", "product_image_id"),
    ):
        if openupgrade.table_exists(env.cr, table):
            continue
        openupgrade.logged_query(
            env.cr,
            f"""
            CREATE TABLE {table} (
                {column1} INTEGER NOT NULL,
                {column2} INTEGER NOT NULL,
                PRIMARY KEY({column1}, {column2})
            );
            CREATE INDEX ON {table} ({column2}, {column1});
            """,
        )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE product_image
        SET product_tmpl_id=product_product.product_tmpl_id
        FROM product_product
        WHERE
            product_image.product_variant_id=product_product.id
        AND
            product_image.product_tmpl_id IS NULL
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO product_image_attribute_value_rel (
            product_image_id, product_template_attribute_value_id
        )
        SELECT
            product_image.id,
            product_variant_combination.product_template_attribute_value_id
        FROM
            product_image
        JOIN
            product_product
            ON product_image.product_variant_id=product_product.id
        JOIN
            product_variant_combination
            ON product_variant_combination.product_product_id=product_product.id
        WHERE
            product_image.product_tmpl_id=product_product.product_tmpl_id
        ON CONFLICT DO NOTHING
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE product_image
        SET has_attribute_value=True
        WHERE id IN (
            SELECT product_image_id FROM product_image_attribute_value_rel
        )
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO product_product_image_rel (product_product_id, product_image_id)
        SELECT product_variant_id, id
        FROM product_image
        WHERE product_variant_id IS NOT NULL AND has_attribute_value
        ON CONFLICT DO NOTHING
        """,
    )


def product_template_suggest_products(env):
    """
    Precompute the stored product.template#suggest_*_products: suggest only when
    the template has no optional/accessory/alternative products
    """
    for field, table in (
        ("suggest_optional_products", "product_optional_rel"),
        ("suggest_accessory_products", "product_accessory_rel"),
        ("suggest_alternative_products", "product_alternative_rel"),
    ):
        openupgrade.add_columns(env, [("product.template", field, "boolean", True)])
        if not openupgrade.table_exists(env.cr, table):
            continue
        openupgrade.logged_query(
            env.cr,
            f"""
            UPDATE product_template
            SET {field}=False
            WHERE id IN (SELECT src_id FROM {table})
            """,
        )


def sale_order_assigned_website_id(env):
    """
    Precompute the stored sale.order#assigned_website_id from sale.order#website_id
    """
    openupgrade.add_columns(
        env, [("sale.order", "assigned_website_id", "many2one", None, "sale_order")]
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE sale_order
        SET assigned_website_id=website_id
        WHERE website_id IS NOT NULL
        """,
    )


def website_show_line_subtotals_tax_selection(env):
    """
    website#show_line_subtotals_tax_selection is required now
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE website
        SET show_line_subtotals_tax_selection='tax_excluded'
        WHERE show_line_subtotals_tax_selection IS NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_fields(env, _renamed_fields)
    openupgrade.rename_xmlids(env.cr, _renamed_xmlids)
    openupgrade.set_xml_ids_noupdate_value(
        env,
        "website_sale",
        ["ir_cron_send_abandoned_email", "ir_cron_send_availability_email"],
        True,
    )
    ir_ui_view_key(env)
    product_document_attached_on_sale(env)
    product_image_attribute_value_ids(env)
    product_template_suggest_products(env)
    sale_order_assigned_website_id(env)
    website_show_line_subtotals_tax_selection(env)

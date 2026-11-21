# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_added_columns = [
    ("product.product", "hs_code", "char"),
    ("product.product", "country_of_origin", "many2one"),
]


def product_product_hs_code_country_of_origin(env):
    """
    hs_code and country_of_origin are stored on the variants now, fill them from
    their template
    """
    if openupgrade.column_exists(env.cr, "product_product", "hs_code"):
        return
    openupgrade.add_columns(env, _added_columns)
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            product_product
        SET
            hs_code=product_template.hs_code,
            country_of_origin=product_template.country_of_origin
        FROM
            product_template
        WHERE
            product_template.id=product_product.product_tmpl_id
        AND (
            product_template.hs_code IS NOT NULL
            OR product_template.country_of_origin IS NOT NULL
        )
        """,
    )


def res_partner_pickup_location_data(env):
    """
    The pickup location data is stored on the pickup address instead of the sale
    order, fill it from the last order delivered to every pickup address
    """
    if (
        openupgrade.column_exists(env.cr, "res_partner", "pickup_location_data")
        or not openupgrade.column_exists(env.cr, "res_partner", "is_pickup_location")
        or not openupgrade.column_exists(env.cr, "sale_order", "pickup_location_data")
    ):
        return
    openupgrade.add_columns(
        env,
        [
            (
                "res.partner",
                "pickup_location_data",
                "json",
                None,
                "res_partner",
                "jsonb",
            )
        ],
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            res_partner
        SET
            pickup_location_data=pickup_orders.pickup_location_data
        FROM (
            SELECT DISTINCT ON (partner_shipping_id)
                partner_shipping_id, pickup_location_data
            FROM
                sale_order
            WHERE
                pickup_location_data IS NOT NULL
            AND
                pickup_location_data NOT IN ('null'::jsonb, '{}'::jsonb)
            ORDER BY
                partner_shipping_id, id DESC
        ) pickup_orders
        WHERE
            pickup_orders.partner_shipping_id=res_partner.id
        AND
            res_partner.is_pickup_location
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    product_product_hs_code_country_of_origin(env)
    res_partner_pickup_location_data(env)

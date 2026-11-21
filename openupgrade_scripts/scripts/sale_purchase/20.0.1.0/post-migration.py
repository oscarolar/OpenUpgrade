# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_SERVICE_TO_PURCHASE = """
    EXISTS (
        SELECT 1
        FROM jsonb_each_text(product_template.service_to_purchase) company_value
        WHERE company_value.value='true'
    )
"""


def product_template_service_tracking(env):
    if not openupgrade.column_exists(
        env.cr, "product_template", "service_to_purchase"
    ):
        return
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE product_template
        SET service_tracking='subcontract'
        WHERE type='service'
        AND purchase_ok
        AND COALESCE(reinvoice_policy, 'no')='no'
        AND COALESCE(service_tracking, 'no')='no'
        AND {_SERVICE_TO_PURCHASE}
        """,
    )
    env.cr.execute(
        f"""
        SELECT id
        FROM product_template
        WHERE service_tracking IS DISTINCT FROM 'subcontract'
        AND {_SERVICE_TO_PURCHASE}
        """
    )
    template_ids = [row[0] for row in env.cr.fetchall()]
    if template_ids:
        openupgrade.message(
            env.cr,
            "sale_purchase",
            "product_template",
            "service_tracking",
            "Products that were subcontracted services in v19 but could not be "
            "set to service_tracking='subcontract' (other tracking, re-invoicing "
            "policy or not purchasable): %s",
            template_ids,
        )


@openupgrade.migrate()
def migrate(env, version):
    product_template_service_tracking(env)

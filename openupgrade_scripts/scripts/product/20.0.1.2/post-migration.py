# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def product_template_attribute_value_excluded_value_ids(env):
    """
    product.template.attribute.exclusion is replaced by the many2many
    product.template.attribute.value#excluded_value_ids, which only supports
    exclusions between values of the same template
    """
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO product_template_attribute_excluded_value_ids_rel (
            product_template_attribute_value_id,
            excluded_product_template_attribute_value_id
        )
        SELECT DISTINCT
            exclusion.product_template_attribute_value_id,
            rel.product_template_attribute_value_id
        FROM product_template_attribute_exclusion exclusion
        JOIN product_attr_exclusion_value_ids_rel rel
            ON rel.product_template_attribute_exclusion_id=exclusion.id
        JOIN product_template_attribute_value ptav
            ON ptav.id=exclusion.product_template_attribute_value_id
        JOIN product_template_attribute_value excluded_ptav
            ON excluded_ptav.id=rel.product_template_attribute_value_id
        WHERE ptav.product_tmpl_id=exclusion.product_tmpl_id
        AND excluded_ptav.product_tmpl_id=exclusion.product_tmpl_id
        AND ptav.attribute_line_id != excluded_ptav.attribute_line_id
        ON CONFLICT DO NOTHING
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    product_template_attribute_value_excluded_value_ids(env)

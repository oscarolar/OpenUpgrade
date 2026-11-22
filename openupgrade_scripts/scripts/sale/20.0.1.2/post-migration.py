# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def product_template_sale_delay(env):
    legacy_column = openupgrade.get_legacy_name("sale_delay")
    if not openupgrade.column_exists(env.cr, "product_template", legacy_column):
        return
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE product_template
        SET sale_delay=(
            SELECT jsonb_object_agg(res_company.id, product_template.{legacy_column})
            FROM res_company
        )
        WHERE COALESCE({legacy_column}, 0) != 0
        """,
    )


def res_company_sale_invoice_policy(env):
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_company
        SET sale_invoice_policy=defaults.value
        FROM (
            SELECT DISTINCT ON (res_company.id)
                res_company.id AS company_id,
                ir_default.json_value::jsonb #>> '{}' AS value
            FROM res_company
            JOIN ir_default
                ON ir_default.company_id=res_company.id
                OR ir_default.company_id IS NULL
            JOIN ir_model_fields
                ON ir_model_fields.id=ir_default.field_id
            WHERE ir_model_fields.model='product.template'
            AND ir_model_fields.name='invoice_policy'
            AND ir_default.user_id IS NULL
            AND ir_default.condition IS NULL
            ORDER BY res_company.id, ir_default.company_id NULLS LAST
        ) defaults
        WHERE defaults.company_id=res_company.id
        AND defaults.value IN ('order', 'delivery')
        """,
    )


def res_company_sale_automatic_invoice(env):
    if env["ir.config_parameter"].get_bool("sale.automatic_invoice"):
        env["res.company"].search([]).write({"sale_automatic_invoice": True})


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "sale", "20.0.1.2/noupdate_changes.xml")
    openupgrade.delete_record_translations(
        env.cr,
        "sale",
        [
            "email_template_edi_sale",
            "email_template_proforma",
            "mail_template_sale_confirmation",
        ],
        ["body_html", "subject"],
    )
    openupgrade.delete_record_translations(
        env.cr,
        "sale",
        ["email_template_proforma"],
        ["name", "description"],
    )
    product_template_sale_delay(env)
    res_company_sale_invoice_policy(env)
    res_company_sale_automatic_invoice(env)

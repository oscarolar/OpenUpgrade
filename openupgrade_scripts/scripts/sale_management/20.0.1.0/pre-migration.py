# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_added_columns = [
    ("sale.order.template.line", "section_uom_id", "many2one"),
]


def sale_order_template_line_section_fields(env):
    if not openupgrade.column_exists(
        env.cr, "sale_order_template_line", "section_qty"
    ):
        openupgrade.logged_query(
            env.cr,
            """
            ALTER TABLE sale_order_template_line
            ADD COLUMN section_qty numeric DEFAULT 0
            """,
        )
        openupgrade.logged_query(
            env.cr,
            """
            ALTER TABLE sale_order_template_line
            ALTER COLUMN section_qty DROP DEFAULT
            """,
        )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE sale_order_template_line
        SET section_qty=1, section_uom_id=%s
        WHERE display_type IN ('line_section', 'line_subsection')
        """,
        (env.ref("uom.product_uom_unit").id,),
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.add_columns(env, _added_columns)
    sale_order_template_line_section_fields(env)

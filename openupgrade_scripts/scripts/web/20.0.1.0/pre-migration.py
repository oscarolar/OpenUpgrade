from openupgradelib import openupgrade


def res_company_report_layout(env):
    """
    The bold, boxed and striped document layouts are removed, their table
    design is now selected with res.company#report_tables_id on top of any
    layout. Switch companies using them to the standard layout with the
    matching table design, and keep the rounded tables of the bubble layout
    """
    if not openupgrade.column_exists(env.cr, "res_company", "report_tables_id"):
        return
    IrModelData = env["ir.model.data"]
    standard_id = IrModelData._xmlid_to_res_id("web.external_layout_standard")
    for layout in ("bold", "boxed", "striped"):
        layout_id = IrModelData._xmlid_to_res_id(f"web.external_layout_{layout}")
        if not layout_id or not standard_id:
            continue
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE
                res_company
            SET
                external_report_layout_id=%s,
                report_tables_id=%s
            WHERE
                external_report_layout_id=%s
            """,
            (standard_id, layout, layout_id),
        )
    bubble_id = IrModelData._xmlid_to_res_id("web.external_layout_bubble")
    if bubble_id:
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE
                res_company
            SET
                report_tables_id='bubble'
            WHERE
                external_report_layout_id=%s
            """,
            (bubble_id,),
        )


@openupgrade.migrate()
def migrate(env, version):
    res_company_report_layout(env)

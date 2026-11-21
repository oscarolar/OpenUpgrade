from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "pos_self_order", "20.0.1.0/noupdate_changes.xml")
    openupgrade.delete_record_translations(
        env.cr,
        "pos_self_order",
        ["delivery_email_template", "takeout_email_template"],
        ["body_html", "description"],
    )

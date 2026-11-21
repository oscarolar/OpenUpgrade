from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "mail_group", "20.0.1.1/noupdate_changes.xml")

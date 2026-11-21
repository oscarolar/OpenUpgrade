from openupgradelib import openupgrade

_renamed_xmlids = [
    ("base_address_extended.menu_res_city", "contacts.menu_res_city"),
]


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_xmlids(env.cr, _renamed_xmlids)

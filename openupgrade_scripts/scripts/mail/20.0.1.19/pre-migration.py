# Copyright 2026 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_xmlids = [
    (
        "mail.action_view_mail_tracking_value",
        "mail_tracking.action_view_mail_tracking_value",
    ),
    ("mail.menu_mail_tracking_value", "mail_tracking.menu_mail_tracking_value"),
    (
        "mail.view_mail_tracking_value_form",
        "mail_tracking.view_mail_tracking_value_form",
    ),
    (
        "mail.view_mail_tracking_value_tree",
        "mail_tracking.view_mail_tracking_value_tree",
    ),
]

_renamed_tables = [
    ("mail_message_res_partner_starred_rel", "mail_message_res_partner_bookmarked_rel"),
]

_added_columns = [
    ("mail.activity", "phone", "char"),
    ("mail.activity", "role_id", "many2one"),
    ("mail.activity", "technical_usage", "selection", "none"),
    ("mail.activity.plan.template", "role_id", "many2one"),
]


def admin_channel_member_xmlid(env):
    """
    Create an xmlid for admin's channel member in the admin channel
    """
    env.cr.execute(
        """
        SELECT id
        FROM discuss_channel_member
        WHERE
        partner_id = (
            SELECT res_id FROM ir_model_data
            WHERE module='base' and name='partner_admin'
        )
        AND channel_id = (
            SELECT res_id FROM ir_model_data
            WHERE module='mail' and name='channel_admin'
        )
        AND NOT EXISTS (
            SELECT id FROM ir_model_data
            WHERE
            module='mail'
            AND name='channel_member_channel_admin_partner_admin'
        )
        """
    )
    for (_id,) in env.cr.fetchall():
        openupgrade.add_xmlid(
            env.cr,
            "mail",
            "channel_member_channel_admin_partner_admin",
            "discuss.channel.member",
            _id,
        )


def mail_tracking(env):
    """
    If there are tracking values, move their model to mail_tracking and install it.
    The values are rendered into the messages in end-migration
    """
    env.cr.execute("SELECT 1 FROM mail_tracking_value LIMIT 1")
    if not env.cr.rowcount:
        return
    openupgrade.update_module_moved_models(
        env.cr, "mail.tracking.value", "mail", "mail_tracking"
    )
    env["ir.module.module"].search(
        [("name", "=", "mail_tracking"), ("state", "=", "uninstalled")]
    ).button_install()


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_xmlids(env.cr, _renamed_xmlids)
    openupgrade.rename_tables(env.cr, _renamed_tables)
    openupgrade.add_columns(env, _added_columns)
    admin_channel_member_xmlid(env)
    mail_tracking(env)

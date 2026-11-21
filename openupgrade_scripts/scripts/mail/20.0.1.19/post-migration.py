# Copyright 2026 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def discuss_channel_member_channel_role(env):
    """
    Set discuss.channel.member#channel_role to 'owner' for backend users who created a
    channel
    """
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE
            discuss_channel_member
        SET
            channel_role='owner'
        FROM
            res_users,
            discuss_channel
        WHERE
            channel_type IN ('group', 'channel')
        AND
            discuss_channel_member.channel_id=discuss_channel.id
        AND
            res_users.partner_id=discuss_channel_member.partner_id
        AND
            res_users.id=discuss_channel.create_uid
        AND
            NOT EXISTS (
                SELECT uid FROM res_groups_users_rel
                WHERE uid=res_users.id AND gid={env.ref("base.group_public").id}
            )
        """,
    )


def mail_activity_type_suggested_next_type_id(env):
    """
    Fill mail.activity.type#suggested_next_type_id from
    mail.activity.type#suggested_next_type_ids
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            mail_activity_type
        SET
            suggested_next_type_id=mail_activity_rel.recommended_id
        FROM (
            SELECT activity_id, min(recommended_id) AS recommended_id
            FROM mail_activity_rel
            GROUP BY activity_id
        ) mail_activity_rel
        WHERE
            mail_activity_rel.activity_id=mail_activity_type.id
        """,
    )


def mail_activity_type_triggered_next_type_id(env):
    """
    Activity types that triggered a next activity suggest it now, as triggering is gone
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            mail_activity_type
        SET
            suggested_next_type_id=triggered_next_type_id
        WHERE
            triggered_next_type_id IS NOT NULL
        AND
            suggested_next_type_id IS NULL
        """,
    )


_mail_post_note_code = """template = env["mail.template"].browse(%(template_id)s)
if records and template.exists():
    records.with_context(
        mail_post_autofollow_author_skip=True,
        mail_post_autofollow=%(autofollow)s,
    ).message_post_with_source(
        template,
        message_type="auto_comment",
        subtype_id=env.ref("mail.mt_note").id,
    )
"""
_mail_post_email_code = """template = env["mail.template"].browse(%(template_id)s)
if records and template.exists():
    for record in records:
        template.send_mail(record.id, force_send=False, raise_exception=False)
"""


def ir_actions_server_mail_post_method(env):
    """
    Server actions of type mail_post always post a comment that notifies followers in
    v20. The ones that logged a note or only sent an email become code actions that
    do what they did in v19
    """
    env.cr.execute(
        """
        SELECT
            id, mail_post_method, template_id, mail_post_autofollow
        FROM
            ir_act_server
        WHERE
            state='mail_post'
        AND
            mail_post_method IN ('email', 'note')
        AND
            template_id IS NOT NULL
        """
    )
    for action_id, method, template_id, autofollow in env.cr.fetchall():
        code = _mail_post_note_code if method == "note" else _mail_post_email_code
        openupgrade.logged_query(
            env.cr,
            "UPDATE ir_act_server SET state='code', code=%s WHERE id=%s",
            (
                code % {"template_id": template_id, "autofollow": bool(autofollow)},
                action_id,
            ),
        )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(
        env,
        "mail",
        "20.0.1.19/noupdate_changes.xml",
        xml_transformation_filename="20.0.1.19/noupdate_changes-transformation.xml",
    )
    discuss_channel_member_channel_role(env)
    mail_activity_type_suggested_next_type_id(env)
    mail_activity_type_triggered_next_type_id(env)
    ir_actions_server_mail_post_method(env)

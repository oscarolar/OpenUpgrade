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


def ir_actions_server_mail_post_method(env):
    """
    Server actions of type mail_post always post a comment in v20. Report the ones
    that sent an email without posting or logged a note, they need a review
    """
    env.cr.execute(
        """
        SELECT
            id, name->>'en_US', mail_post_method
        FROM
            ir_act_server
        WHERE
            state='mail_post'
        AND
            mail_post_method IN ('email', 'note')
        """
    )
    for action_id, name, method in env.cr.fetchall():
        openupgrade.message(
            env.cr,
            "mail",
            "ir_act_server",
            "mail_post_method",
            "Server action %s (%s) used method '%s' in v19, in v20 it posts a comment "
            "that notifies followers",
            action_id,
            name,
            method,
        )


def _tracking_escape(expression):
    return (
        f"replace(replace(replace({expression}, '&', '&amp;'), '<', '&lt;'), "
        "'>', '&gt;')"
    )


def _tracking_value(prefix):
    """
    Return the SQL expression that formats the old or new value of a tracking record
    """
    number = "trim_scale(round(COALESCE({}, 0)::numeric, {}))::text"
    return _tracking_escape(
        f"""
        CASE COALESCE(field.ttype, value.field_info->>'type')
        WHEN 'boolean' THEN
            CASE WHEN value.{prefix}_value_integer = 1 THEN 'Yes' ELSE 'No' END
        WHEN 'integer' THEN
            COALESCE(value.{prefix}_value_integer, 0)::text
        WHEN 'float' THEN
            {number.format(f"value.{prefix}_value_float", 6)}
        WHEN 'monetary' THEN
            concat_ws(
                ' ', round(COALESCE(value.{prefix}_value_float, 0)::numeric, 2)::text,
                currency.symbol
            )
        WHEN 'date' THEN
            COALESCE(value.{prefix}_value_datetime::date::text, 'None')
        WHEN 'datetime' THEN
            COALESCE(
                to_char(value.{prefix}_value_datetime, 'YYYY-MM-DD HH24:MI:SS')
                || ' UTC',
                'None'
            )
        WHEN 'text' THEN
            COALESCE(NULLIF(value.{prefix}_value_text, ''), 'None')
        WHEN 'html' THEN
            COALESCE(NULLIF(value.{prefix}_value_text, ''), 'None')
        ELSE
            COALESCE(NULLIF(value.{prefix}_value_char, ''), 'None')
        END
        """
    )


def mail_message_tracking_body(env):
    """
    v20 does not render mail.tracking.value records in the chatter any more, tracked
    changes are part of the body of the message. Append the tracking values of existing
    messages to their body the way mail.mail_tracking_template does
    """
    lang = env.ref("base.main_company").partner_id.lang or "en_US"
    label = _tracking_escape(
        """
        COALESCE(
            field.field_description->>%(lang)s, field.field_description->>'en_US',
            value.field_info->>'desc', field.name, value.field_info->>'name', ''
        )
        """
    )
    currency_join = "LEFT JOIN res_currency currency ON FALSE"
    if openupgrade.column_exists(env.cr, "mail_tracking_value", "currency_id"):
        currency_join = (
            "LEFT JOIN res_currency currency ON currency.id=value.currency_id"
        )
    env.cr.execute(
        "SELECT min(mail_message_id), max(mail_message_id) FROM mail_tracking_value"
    )
    min_id, max_id = env.cr.fetchone()
    if min_id is None:
        return
    step = 500000
    for start in range(min_id, max_id + 1, step):
        openupgrade.logged_query(
            env.cr,
            f"""
            UPDATE
                mail_message
            SET
                body=COALESCE(mail_message.body, '') || tracking.html
            FROM (
                SELECT
                    value.mail_message_id,
                    '<div>' || string_agg(
                        {_tracking_value("old")} || ' → <b>'
                        || {_tracking_value("new")} || '</b> <i>(' || {label}
                        || ')</i>',
                        '<br>' ORDER BY value.id DESC
                    ) || '</div>' AS html
                FROM
                    mail_tracking_value value
                LEFT JOIN
                    ir_model_fields field ON field.id=value.field_id
                {currency_join}
                WHERE
                    value.mail_message_id >= %(start)s
                AND
                    value.mail_message_id < %(stop)s
                GROUP BY
                    value.mail_message_id
            ) tracking
            WHERE
                mail_message.id=tracking.mail_message_id
            """,
            {"lang": lang, "start": start, "stop": start + step},
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
    mail_message_tracking_body(env)

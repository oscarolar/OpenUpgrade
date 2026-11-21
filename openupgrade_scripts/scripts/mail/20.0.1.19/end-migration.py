# Copyright 2026 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

from odoo.tools.translate import code_translations


def _tracking_escape(expression):
    return (
        f"replace(replace(replace({expression}, '&', '&amp;'), '<', '&lt;'), "
        "'>', '&gt;')"
    )


def _tracking_value(prefix):
    """
    Return the SQL expression that formats the old or new value of a tracking record
    """
    amount = (
        f"round(COALESCE(value.{prefix}_value_float, 0)::numeric, "
        "COALESCE(currency.decimal_places, 2))::text"
    )
    return _tracking_escape(
        f"""
        CASE field.ttype
        WHEN 'boolean' THEN
            CASE WHEN value.{prefix}_value_integer = 1
            THEN %(yes)s ELSE %(no)s END
        WHEN 'integer' THEN
            COALESCE(value.{prefix}_value_integer, 0)::text
        WHEN 'float' THEN
            trim_scale(
                round(COALESCE(value.{prefix}_value_float, 0)::numeric, 6)
            )::text
        WHEN 'monetary' THEN
            CASE
            WHEN currency.id IS NULL THEN {amount}
            WHEN currency.position = 'before'
            THEN currency.symbol || ' ' || {amount}
            ELSE {amount} || ' ' || currency.symbol
            END
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


def mail_message_tracking(env):
    """
    v20 does not render mail.tracking.value records in the chatter any more, tracked
    changes are part of the body of the message. Append the tracking values of existing
    messages to their body the way mail.mail_tracking_template does, and set
    message_type=tracking for the notifications among them.

    Values of fields restricted to groups and of fields that don't exist any more
    are only shown to the users allowed to see them, so they stay out of the body.
    This needs the fields of all modules, so it can't run before end-migration.

    Every message is written once, and not again if the script runs twice
    """
    marker = openupgrade.get_legacy_name("mail_tracking_rendered")
    if openupgrade.table_exists(env.cr, marker):
        return
    env.cr.execute(
        "SELECT min(mail_message_id), max(mail_message_id) FROM mail_tracking_value"
    )
    min_id, max_id = env.cr.fetchone()
    if min_id is None:
        return
    env.cr.execute(
        """
        SELECT id, model, name FROM ir_model_fields
        WHERE id IN (SELECT field_id FROM mail_tracking_value)
        """
    )
    visible_field_ids = [
        field_id
        for field_id, model, name in env.cr.fetchall()
        if model in env
        and name in env[model]._fields
        and not env[model]._fields[name].groups
    ]
    lang = env.ref("base.main_company").partner_id.lang or "en_US"
    translations = code_translations.get_python_translations("mail", lang)
    label = _tracking_escape(
        """
        COALESCE(
            field.field_description->>%(lang)s, field.field_description->>'en_US',
            field.name
        )
        """
    )
    currency_join = "LEFT JOIN res_currency currency ON FALSE"
    if openupgrade.column_exists(env.cr, "mail_tracking_value", "currency_id"):
        currency_join = (
            "LEFT JOIN res_currency currency ON currency.id=value.currency_id"
        )
    step = 500000
    for start in range(min_id, max_id + 1, step):
        openupgrade.logged_query(
            env.cr,
            f"""
            UPDATE
                mail_message
            SET
                message_type=CASE
                    WHEN mail_message.message_type='notification' THEN 'tracking'
                    ELSE mail_message.message_type
                END,
                body=COALESCE(mail_message.body, '') || COALESCE(tracking.html, '')
            FROM (
                SELECT
                    value.mail_message_id,
                    '<div>' || string_agg(
                        {_tracking_value("old")} || ' → <b>'
                        || {_tracking_value("new")} || '</b> <i>(' || {label}
                        || ')</i>',
                        '<br>' ORDER BY value.id DESC
                    ) FILTER (
                        WHERE field.id=ANY(%(visible_field_ids)s)
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
            {
                "lang": lang,
                "visible_field_ids": visible_field_ids,
                "start": start,
                "stop": start + step,
                "yes": translations.get("Yes", "Yes"),
                "no": translations.get("No", "No"),
            },
        )
    env.cr.execute(f"CREATE TABLE {marker} AS SELECT now() AS rendered")


@openupgrade.migrate()
def migrate(env, version):
    mail_message_tracking(env)

# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def event_address_inline(env):
    """
    event.event#address_inline is gone in favour of contact_address_inline, replace
    it in the templates, including the ones created by the user
    """
    for table, column in (("sms_template", "body"), ("mail_template", "body_html")):
        openupgrade.logged_query(
            env.cr,
            f"""
            UPDATE {table}
            SET {column}=replace(
                {column}::text,
                'event_id.address_inline',
                'event_id.contact_address_inline'
            )::jsonb
            WHERE {column}::text LIKE '%%event_id.address_inline%%'
            """,
        )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "event_sms", "20.0.1.0/noupdate_changes.xml")
    openupgrade.delete_record_translations(
        env.cr,
        "event_sms",
        ["sms_template_data_event_reminder"],
        ["body"],
    )
    event_address_inline(env)

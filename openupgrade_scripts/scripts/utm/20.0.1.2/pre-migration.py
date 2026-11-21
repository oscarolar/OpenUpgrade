# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_xmlids = [
    ("crm_livechat.utm_source_livechat", "utm.utm_source_livechat"),
]

_new_records = [
    ("utm_medium_messaging", "utm.medium", "Messaging"),
    ("utm_medium_social_media", "utm.medium", "Social Media"),
    ("utm_source_google", "utm.source", "Google"),
    ("utm_source_instagram", "utm.source", "Instagram"),
    ("utm_source_livechat", "utm.source", "Livechat"),
    ("utm_source_survey", "utm.source", "Survey"),
    ("utm_source_youtube", "utm.source", "YouTube"),
]


def utm_medium_runtime_xmlids(env):
    """
    Protect the mediums created at runtime by _fetch_or_create_utm_medium, whose
    xmlids are not part of the module data, from being deleted by the update
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            ir_model_data
        SET
            noupdate=TRUE
        WHERE
            module='utm'
        AND
            model='utm.medium'
        AND
            noupdate IS NOT TRUE
        """,
    )


def utm_new_records_xmlids(env):
    """
    Link the new mediums and sources of the module data to existing records with
    the same name, as names are unique and a duplicate would be created otherwise
    """
    for xmlid, model, name in _new_records:
        table = model.replace(".", "_")
        env.cr.execute(
            f"""
            SELECT id
            FROM {table}
            WHERE lower(name)=lower(%s)
            ORDER BY name=%s DESC, id
            LIMIT 1
            """,
            (name, name),
        )
        row = env.cr.fetchone()
        if row:
            openupgrade.add_xmlid(env.cr, "utm", xmlid, model, row[0], noupdate=True)


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_xmlids(env.cr, _renamed_xmlids)
    utm_medium_runtime_xmlids(env)
    utm_new_records_xmlids(env)

# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def mailing_utm_reference(env):
    """
    The leads of a mailing are found by utm_reference instead of
    the utm source of the mailing. Fill it for sources used by a single mailing
    """
    for table in ("crm_lead",):
        openupgrade.logged_query(
            env.cr,
            f"""
            UPDATE {table}
            SET utm_reference='mailing.mailing,' || mailing_mailing.id
            FROM mailing_mailing
            WHERE {table}.source_id=mailing_mailing.source_id
            AND {table}.utm_reference IS NULL
            AND mailing_mailing.source_id IN (
                SELECT source_id
                FROM mailing_mailing
                WHERE source_id IS NOT NULL
                GROUP BY source_id
                HAVING COUNT(*)=1
            )
            """,
        )


@openupgrade.migrate()
def migrate(env, version):
    mailing_utm_reference(env)

# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def crm_lead_utm_reference(env):
    """
    Fill crm.lead#utm_reference from crm.lead#origin_survey_id
    """
    if not openupgrade.column_exists(env.cr, "crm_lead", "origin_survey_id"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            crm_lead
        SET
            utm_reference='survey.survey,' || origin_survey_id
        WHERE
            origin_survey_id IS NOT NULL
        AND
            utm_reference IS NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    crm_lead_utm_reference(env)

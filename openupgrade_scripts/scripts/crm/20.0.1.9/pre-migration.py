# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def crm_lead_duration_tracking(env):
    """
    duration_tracking is stored now: minutes spent in each previous stage, the
    current stage (s) and the date it was set (d). It was computed on the fly
    from the tracking values of the stage, which is the source to fill it
    """
    openupgrade.logged_query(
        env.cr,
        "ALTER TABLE crm_lead ADD COLUMN IF NOT EXISTS duration_tracking jsonb",
    )
    openupgrade.logged_query(
        env.cr,
        """
        WITH tracking AS (
            SELECT
                crm_lead.id AS lead_id,
                COALESCE(mail_tracking_value.old_value_integer, 0) AS stage_id,
                mail_tracking_value.create_date,
                COALESCE(
                    LAG(mail_tracking_value.create_date) OVER (
                        PARTITION BY crm_lead.id ORDER BY mail_tracking_value.id
                    ),
                    crm_lead.create_date
                ) AS previous_date
            FROM mail_tracking_value
            JOIN mail_message
                ON mail_message.id=mail_tracking_value.mail_message_id
            JOIN crm_lead ON crm_lead.id=mail_message.res_id
            WHERE mail_message.model='crm.lead'
            AND mail_tracking_value.field_id=(
                SELECT id FROM ir_model_fields
                WHERE model='crm.lead' AND name='stage_id'
            )
        ),
        stage_duration AS (
            SELECT
                lead_id,
                stage_id,
                SUM(
                    GREATEST(EXTRACT(EPOCH FROM create_date - previous_date), 0)
                ) AS seconds
            FROM tracking
            GROUP BY lead_id, stage_id
        ),
        lead_duration AS (
            SELECT
                lead_id,
                jsonb_object_agg(stage_id::text, (seconds / 60)::integer) AS duration
            FROM stage_duration
            GROUP BY lead_id
        ),
        last_change AS (
            SELECT lead_id, MAX(create_date) AS create_date
            FROM tracking
            GROUP BY lead_id
        )
        UPDATE crm_lead
        SET duration_tracking=COALESCE(lead_duration.duration, '{}'::jsonb)
            || jsonb_build_object(
                's', COALESCE(crm_lead.stage_id, 0),
                'd', to_char(
                    COALESCE(
                        last_change.create_date,
                        crm_lead.create_date,
                        now() AT TIME ZONE 'UTC'
                    ),
                    'YYYY-MM-DD HH24:MI:SS'
                )
            )
        FROM crm_lead crm_lead2
        LEFT JOIN lead_duration ON lead_duration.lead_id=crm_lead2.id
        LEFT JOIN last_change ON last_change.lead_id=crm_lead2.id
        WHERE crm_lead.id=crm_lead2.id
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    crm_lead_duration_tracking(env)

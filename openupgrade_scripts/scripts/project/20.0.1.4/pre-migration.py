# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade
from psycopg2 import sql

_added_columns = [
    ("project.collaborator", "access_mode", "selection"),
    ("project.project", "date_last_stage_update", "datetime"),
    ("project.project", "duration_tracking", "json"),
    ("project.task", "duration_tracking", "json"),
]


def project_collaborator_access_mode(env):
    """
    Fill project.collaborator#access_mode from project.collaborator#limited_access
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            project_collaborator
        SET
            access_mode=CASE
                WHEN limited_access IS TRUE THEN 'edit'
                ELSE 'advanced_edit'
            END
        """,
    )


def duration_tracking(env, model, table):
    """
    Fill the now stored duration_tracking from the stage trackings: minutes spent per
    stage, current stage ('s') and date of the last stage change ('d')
    """
    openupgrade.logged_query(
        env.cr,
        sql.SQL(
            """
            WITH tracking AS (
                SELECT
                    mail_message.res_id,
                    mail_tracking_value.create_date,
                    COALESCE(mail_tracking_value.old_value_integer, 0) AS stage_id,
                    LAG(mail_tracking_value.create_date) OVER (
                        PARTITION BY mail_message.res_id
                        ORDER BY mail_tracking_value.id
                    ) AS previous_date
                FROM
                    mail_tracking_value
                JOIN
                    mail_message
                    ON mail_message.id=mail_tracking_value.mail_message_id
                JOIN
                    ir_model_fields
                    ON ir_model_fields.id=mail_tracking_value.field_id
                WHERE
                    mail_message.model=%(model)s
                AND
                    ir_model_fields.model=%(model)s
                AND
                    ir_model_fields.name='stage_id'
            ),
            duration AS (
                SELECT
                    tracking.res_id,
                    tracking.stage_id,
                    SUM(FLOOR(GREATEST(EXTRACT(EPOCH FROM (
                        tracking.create_date - COALESCE(
                            tracking.previous_date,
                            record.create_date,
                            tracking.create_date
                        )
                    )), 0) / 60))::integer AS minutes,
                    MAX(tracking.create_date) AS last_date
                FROM
                    tracking
                JOIN
                    {table} record
                    ON record.id=tracking.res_id
                GROUP BY
                    tracking.res_id, tracking.stage_id
            ),
            summary AS (
                SELECT
                    res_id,
                    jsonb_object_agg(stage_id::text, minutes) AS durations,
                    MAX(last_date) AS last_date
                FROM
                    duration
                GROUP BY
                    res_id
            )
            UPDATE
                {table} record
            SET
                duration_tracking=COALESCE(summary.durations, '{{}}'::jsonb)
                || jsonb_build_object(
                    'd',
                    to_char(
                        COALESCE(
                            summary.last_date,
                            record.create_date,
                            now() AT TIME ZONE 'UTC'
                        ),
                        'YYYY-MM-DD HH24:MI:SS'
                    ),
                    's',
                    COALESCE(record.stage_id, 0)
                )
            FROM
                {table} record2
            LEFT JOIN
                summary
                ON summary.res_id=record2.id
            WHERE
                record2.id=record.id
            """
        ).format(table=sql.Identifier(table)),
        {"model": model},
    )


def project_project_date_last_stage_update(env):
    """
    Set project.project#date_last_stage_update to the date of the last stage change
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            project_project
        SET
            date_last_stage_update=(duration_tracking->>'d')::timestamp
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.add_columns(env, _added_columns)
    project_collaborator_access_mode(env)
    duration_tracking(env, "project.project", "project_project")
    duration_tracking(env, "project.task", "project_task")
    project_project_date_last_stage_update(env)

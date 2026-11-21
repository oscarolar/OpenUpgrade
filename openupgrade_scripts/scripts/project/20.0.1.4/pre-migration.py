# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade
from psycopg2 import sql

_chunk_size = 50000

_added_columns = [
    ("project.collaborator", "access_mode", "selection"),
    ("project.project", "date_last_stage_update", "datetime"),
    ("project.project", "duration_tracking", "json"),
    ("project.task", "duration_tracking", "json"),
]


def project_collaborator_access_mode(env):
    """
    Collaborators had edit access on all the tasks of the project, which is
    advanced_edit. The ones with limited access only reached the tasks they
    follow: no access mode is that narrow, so they are moved to a legacy table and
    stop being collaborators, keeping the portal access to the tasks they follow
    """
    legacy_table = openupgrade.get_legacy_name("project_collaborator_limited")
    openupgrade.logged_query(
        env.cr,
        sql.SQL(
            "CREATE TABLE IF NOT EXISTS {legacy_table} AS "
            "SELECT * FROM project_collaborator WHERE limited_access"
        ).format(legacy_table=sql.Identifier(legacy_table)),
    )
    env.cr.execute(
        """
        SELECT
            project_project.id,
            project_project.name->>'en_US',
            string_agg(
                res_partner.name || ' (id ' || res_partner.id || ')', ', '
                ORDER BY res_partner.id
            )
        FROM project_collaborator
        JOIN project_project ON project_project.id = project_collaborator.project_id
        JOIN res_partner ON res_partner.id = project_collaborator.partner_id
        WHERE project_collaborator.limited_access
        GROUP BY project_project.id
        ORDER BY project_project.id
        """
    )
    for project_id, name, partners in env.cr.fetchall():
        openupgrade.message(
            env.cr,
            "project",
            "project_collaborator",
            "access_mode",
            "Project %s (id %s): the collaborators with limited access are "
            "removed, they keep the tasks they follow in the portal but can't "
            "edit them through project sharing anymore: %s",
            name,
            project_id,
            partners,
        )
    openupgrade.logged_query(
        env.cr, "DELETE FROM project_collaborator WHERE limited_access"
    )
    openupgrade.logged_query(
        env.cr, "UPDATE project_collaborator SET access_mode = 'advanced_edit'"
    )


def duration_tracking(env, model, table):
    """
    Fill the now stored duration_tracking from the stage trackings: minutes spent per
    stage, current stage ('s') and date of the last stage change ('d')
    """
    env.cr.execute(
        sql.SQL("SELECT MIN(id), MAX(id) FROM {table}").format(
            table=sql.Identifier(table)
        )
    )
    min_id, max_id = env.cr.fetchone()
    for start in range(min_id or 0, (max_id or -1) + 1, _chunk_size):
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
                    AND
                        mail_message.res_id BETWEEN %(start)s AND %(end)s
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
                AND
                    record2.id BETWEEN %(start)s AND %(end)s
                """
            ).format(table=sql.Identifier(table)),
            {"model": model, "start": start, "end": start + _chunk_size - 1},
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

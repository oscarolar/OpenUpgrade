# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)


def hr_applicant_recruiter_id(env):
    """
    Fill hr.applicant#recruiter_id (hr.employee) from the employee of
    hr.applicant#user_id (res.users), preferring the employee of the applicant's
    company
    """
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE hr_applicant
        ADD COLUMN IF NOT EXISTS recruiter_id integer
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        WITH pairs AS (
            SELECT DISTINCT user_id, company_id
            FROM hr_applicant
            WHERE user_id IS NOT NULL
        ),
        mapping AS (
            SELECT DISTINCT ON (pairs.user_id, pairs.company_id)
                pairs.user_id, pairs.company_id, hr_employee.id AS employee_id
            FROM pairs
            JOIN hr_employee ON hr_employee.user_id = pairs.user_id
            ORDER BY
                pairs.user_id,
                pairs.company_id,
                (hr_employee.company_id = pairs.company_id) DESC NULLS LAST,
                hr_employee.active DESC NULLS LAST,
                hr_employee.id
        )
        UPDATE hr_applicant
        SET recruiter_id = mapping.employee_id
        FROM mapping
        WHERE
            hr_applicant.user_id = mapping.user_id
            AND hr_applicant.company_id IS NOT DISTINCT FROM mapping.company_id
        """,
    )
    env.cr.execute(
        """
        SELECT COUNT(*), COUNT(DISTINCT user_id)
        FROM hr_applicant
        WHERE user_id IS NOT NULL AND recruiter_id IS NULL
        """
    )
    applicants, users = env.cr.fetchone()
    if applicants:
        _logger.warning(
            "hr_recruitment: %s applicants lose their recruiter because %s users "
            "have no employee; the previous value stays in hr_applicant.user_id",
            applicants,
            users,
        )


def hr_applicant_duration_tracking(env):
    """
    Fill hr.applicant#duration_tracking, which is stored now, from the stage
    trackings v19 used to compute it: minutes per stage, current stage and date
    of the last stage change
    """
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE hr_applicant
        ADD COLUMN IF NOT EXISTS duration_tracking jsonb
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        WITH trackings AS (
            SELECT
                mail_message.res_id,
                mail_tracking_value.id,
                mail_tracking_value.create_date,
                COALESCE(mail_tracking_value.old_value_integer, 0) AS stage_id
            FROM mail_tracking_value
            JOIN mail_message
                ON mail_message.id = mail_tracking_value.mail_message_id
            JOIN ir_model_fields
                ON ir_model_fields.id = mail_tracking_value.field_id
            WHERE
                mail_message.model = 'hr.applicant'
                AND ir_model_fields.model = 'hr.applicant'
                AND ir_model_fields.name = 'stage_id'
        ),
        intervals AS (
            SELECT
                trackings.res_id,
                trackings.stage_id,
                trackings.create_date - COALESCE(
                    LAG(trackings.create_date) OVER (
                        PARTITION BY trackings.res_id ORDER BY trackings.id
                    ),
                    hr_applicant.create_date,
                    trackings.create_date
                ) AS duration
            FROM trackings
            JOIN hr_applicant ON hr_applicant.id = trackings.res_id
        ),
        stage_minutes AS (
            SELECT
                res_id,
                stage_id,
                GREATEST(
                    FLOOR(EXTRACT(EPOCH FROM SUM(duration)) / 60), 0
                )::integer AS minutes
            FROM intervals
            GROUP BY res_id, stage_id
        ),
        durations AS (
            SELECT
                res_id, jsonb_object_agg(stage_id::text, minutes) AS durations
            FROM stage_minutes
            GROUP BY res_id
        ),
        last_changes AS (
            SELECT res_id, MAX(create_date) AS last_change
            FROM trackings
            GROUP BY res_id
        )
        UPDATE hr_applicant
        SET duration_tracking = computed.duration_tracking
        FROM (
            SELECT
                hr_applicant.id,
                COALESCE(durations.durations, '{}'::jsonb) || jsonb_build_object(
                    's', COALESCE(hr_applicant.stage_id, 0),
                    'd', to_char(
                        COALESCE(
                            last_changes.last_change,
                            hr_applicant.create_date,
                            now() AT TIME ZONE 'UTC'
                        ),
                        'YYYY-MM-DD HH24:MI:SS'
                    )
                ) AS duration_tracking
            FROM hr_applicant
            LEFT JOIN durations ON durations.res_id = hr_applicant.id
            LEFT JOIN last_changes ON last_changes.res_id = hr_applicant.id
        ) AS computed
        WHERE computed.id = hr_applicant.id
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    hr_applicant_recruiter_id(env)
    hr_applicant_duration_tracking(env)

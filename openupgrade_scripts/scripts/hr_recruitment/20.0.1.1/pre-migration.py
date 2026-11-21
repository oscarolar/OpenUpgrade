# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_chunk_size = 50000


def hr_applicant_recruiter_id(env):
    """
    Fill hr.applicant#recruiter_id (hr.employee) from the employee that
    hr.applicant#user_id (res.users) has in the company of the applicant.
    Applicants whose user has no employee there are left without recruiter and
    reported
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
            JOIN hr_employee
                ON hr_employee.user_id = pairs.user_id
                AND (
                    pairs.company_id IS NULL
                    OR hr_employee.company_id = pairs.company_id
                )
            ORDER BY
                pairs.user_id,
                pairs.company_id,
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
        SELECT res_users.login, res_company.name, COUNT(*)
        FROM hr_applicant
        JOIN res_users ON res_users.id = hr_applicant.user_id
        LEFT JOIN res_company ON res_company.id = hr_applicant.company_id
        WHERE hr_applicant.recruiter_id IS NULL
        GROUP BY res_users.login, res_company.name
        ORDER BY res_users.login, res_company.name
        """
    )
    for login, company, count in env.cr.fetchall():
        openupgrade.message(
            env.cr,
            "hr_recruitment",
            "hr_applicant",
            "recruiter_id",
            "%s applicants of the company %s are left without recruiter: their "
            "user %s has no employee in that company. The user stays in the "
            "column user_id",
            count,
            company,
            login,
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
    env.cr.execute("SELECT MIN(id), MAX(id) FROM hr_applicant")
    min_id, max_id = env.cr.fetchone()
    for start in range(min_id or 0, (max_id or -1) + 1, _chunk_size):
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
                    AND mail_message.res_id BETWEEN %(start)s AND %(end)s
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
                WHERE hr_applicant.id BETWEEN %(start)s AND %(end)s
            ) AS computed
            WHERE computed.id = hr_applicant.id
            """,
            {"start": start, "end": start + _chunk_size - 1},
        )


@openupgrade.migrate()
def migrate(env, version):
    hr_applicant_recruiter_id(env)
    hr_applicant_duration_tracking(env)

# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_models = [
    ("hr.contract.type", "hr.employee.type"),
]

_renamed_tables = [
    ("hr_contract_type", "hr_employee_type"),
]

_renamed_fields = [
    ("hr.version", "hr_version", "contract_type_id", "employee_type_id"),
    ("hr.job", "hr_job", "contract_type_id", "employee_type_id"),
]

_added_columns = [
    ("hr.version", "tz", "selection"),
    ("hr.employee", "birthday_month", "selection"),
]


def hr_version_tz(env):
    """
    Fill hr.version#tz, which was related to the employee's timezone
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_version
        SET tz = COALESCE(resource_resource.tz, resource_calendar.tz, 'UTC')
        FROM hr_version hr_version2
        LEFT JOIN hr_employee ON hr_employee.id = hr_version2.employee_id
        LEFT JOIN resource_resource
            ON resource_resource.id = hr_employee.resource_id
        LEFT JOIN resource_calendar
            ON resource_calendar.id = hr_version2.resource_calendar_id
        WHERE hr_version.id = hr_version2.id
        """,
    )


def hr_version_resource_calendar_id(env):
    """
    Versions without calendar were fully flexible, which is a calendar of type
    undefined without hours target in v20. Assign one per company before the ORM
    fills the now required field with the calendar of the company, and use it for
    the resource of the employee too
    """
    env.cr.execute(
        """
        SELECT DISTINCT company_id
        FROM hr_version
        WHERE resource_calendar_id IS NULL
        """
    )
    for (company_id,) in env.cr.fetchall():
        env.cr.execute(
            """
            SELECT id
            FROM resource_calendar
            WHERE company_id IS NOT DISTINCT FROM %s
            AND calendar_type = 'undefined'
            AND COALESCE(hours_per_week, 0) = 0
            AND COALESCE(hours_per_day, 0) = 0
            AND active
            ORDER BY id
            LIMIT 1
            """,
            (company_id,),
        )
        row = env.cr.fetchone()
        if not row:
            env.cr.execute(
                """
                INSERT INTO resource_calendar (
                    name, company_id, calendar_type, active,
                    hours_per_week, hours_per_day, days_per_week,
                    full_time_required_hours, work_time_rate,
                    create_uid, create_date, write_uid, write_date
                )
                SELECT
                    'Fully Flexible', %(company_id)s, 'undefined', TRUE,
                    0, 0, 0,
                    COALESCE(
                        (
                            SELECT resource_calendar.hours_per_week
                            FROM res_company
                            JOIN resource_calendar
                                ON resource_calendar.id
                                = res_company.resource_calendar_id
                            WHERE res_company.id = %(company_id)s
                        ),
                        0
                    ),
                    0,
                    %(uid)s, NOW() AT TIME ZONE 'UTC',
                    %(uid)s, NOW() AT TIME ZONE 'UTC'
                RETURNING id
                """,
                {"company_id": company_id, "uid": env.uid},
            )
            row = env.cr.fetchone()
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE resource_resource
            SET calendar_id = %(calendar_id)s
            FROM hr_employee
            JOIN hr_version ON hr_version.id = hr_employee.current_version_id
            WHERE hr_employee.resource_id = resource_resource.id
            AND hr_version.resource_calendar_id IS NULL
            AND hr_version.company_id IS NOT DISTINCT FROM %(company_id)s
            """,
            {"calendar_id": row[0], "company_id": company_id},
        )
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE hr_version
            SET resource_calendar_id = %(calendar_id)s
            WHERE resource_calendar_id IS NULL
            AND company_id IS NOT DISTINCT FROM %(company_id)s
            """,
            {"calendar_id": row[0], "company_id": company_id},
        )


def hr_employee_birthday_month(env):
    """
    Precompute hr.employee#birthday_month
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_employee
        SET birthday_month = COALESCE(EXTRACT(MONTH FROM birthday)::int::varchar, '0')
        """,
    )


def hr_version_sex(env):
    """
    Empty hr.version#sex for the removed value 'other'
    """
    openupgrade.logged_query(
        env.cr, "UPDATE hr_version SET sex = NULL WHERE sex = 'other'"
    )


def mail_activity_plan_template_responsible_type(env):
    """
    The responsible type 'coach' is removed with ondelete=cascade, ask for the
    responsible at launch instead of losing the templates
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE mail_activity_plan_template
        SET responsible_type = 'on_demand'
        WHERE responsible_type = 'coach'
        """,
    )


def hr_job_company_id(env):
    """
    hr.job#company_id is required now: use the company of the department, else the
    company where most employees have the job, else the main company
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_job
        SET company_id = COALESCE(
            (
                SELECT hr_department.company_id
                FROM hr_department
                WHERE hr_department.id = hr_job.department_id
            ),
            (
                SELECT hr_version.company_id
                FROM hr_version
                WHERE hr_version.job_id = hr_job.id
                AND hr_version.company_id IS NOT NULL
                GROUP BY hr_version.company_id
                ORDER BY count(*) DESC, hr_version.company_id
                LIMIT 1
            ),
            (
                SELECT id FROM res_company
                ORDER BY parent_id IS NOT NULL, id
                LIMIT 1
            )
        )
        WHERE company_id IS NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_models(env.cr, _renamed_models)
    openupgrade.rename_tables(env.cr, _renamed_tables)
    openupgrade.rename_fields(env, _renamed_fields)
    openupgrade.add_columns(env, _added_columns)
    hr_version_tz(env)
    hr_version_resource_calendar_id(env)
    hr_employee_birthday_month(env)
    hr_version_sex(env)
    mail_activity_plan_template_responsible_type(env)
    hr_job_company_id(env)

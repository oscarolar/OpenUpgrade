# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

import psycopg2
from openupgradelib import openupgrade
from psycopg2 import sql

_logger = logging.getLogger(__name__)

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


def _hr_job_references(env):
    """
    Return the foreign keys pointing to hr_job as (table, column, has_id,
    has_company_id)
    """
    env.cr.execute(
        """
        SELECT
            pg_class.relname,
            pg_attribute.attname,
            EXISTS (
                SELECT 1 FROM pg_attribute id_attribute
                WHERE id_attribute.attrelid = pg_class.oid
                AND id_attribute.attname = 'id'
                AND NOT id_attribute.attisdropped
            ),
            EXISTS (
                SELECT 1 FROM pg_attribute company_attribute
                WHERE company_attribute.attrelid = pg_class.oid
                AND company_attribute.attname = 'company_id'
                AND NOT company_attribute.attisdropped
            )
        FROM pg_constraint
        JOIN pg_class ON pg_class.oid = pg_constraint.conrelid
        JOIN pg_attribute
            ON pg_attribute.attrelid = pg_constraint.conrelid
            AND pg_attribute.attnum = pg_constraint.conkey[1]
        WHERE pg_constraint.contype = 'f'
        AND pg_constraint.confrelid = 'hr_job'::regclass
        AND pg_class.relname != 'hr_job'
        ORDER BY pg_class.relname, pg_attribute.attname
        """
    )
    return env.cr.fetchall()


def _table_columns(env, table):
    env.cr.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s AND column_name != 'id'
        ORDER BY ordinal_position
        """,
        (table,),
    )
    return [row[0] for row in env.cr.fetchall()]


def _hr_job_copy_relations(env, references, job_id, target_id):
    """
    Add the many2many relations of a job to another one
    """
    for table, column, has_id, _has_company in references:
        if has_id:
            continue
        others = [name for name in _table_columns(env, table) if name != column]
        if not others:
            continue
        other_columns = sql.SQL(", ").join(map(sql.Identifier, others))
        openupgrade.logged_query(
            env.cr,
            sql.SQL(
                """
                INSERT INTO {table} ({column}, {others})
                SELECT %s, {others} FROM {table} WHERE {column} = %s
                ON CONFLICT DO NOTHING
                """
            ).format(
                table=sql.Identifier(table),
                column=sql.Identifier(column),
                others=other_columns,
            ),
            (target_id, job_id),
        )


def _hr_job_clone(env, references, job_id, company_id):
    """
    Copy a job without department into a company, with its own mail alias and
    the same many2many relations
    """
    columns = _table_columns(env, "hr_job")
    values = [
        sql.Literal(company_id)
        if name == "company_id"
        else sql.SQL("NULL")
        if name == "department_id"
        else sql.Identifier(name)
        for name in columns
    ]
    env.cr.execute(
        sql.SQL(
            "INSERT INTO hr_job ({columns}) SELECT {values} FROM hr_job "
            "WHERE id = %s RETURNING id"
        ).format(
            columns=sql.SQL(", ").join(map(sql.Identifier, columns)),
            values=sql.SQL(", ").join(values),
        ),
        (job_id,),
    )
    clone_id = env.cr.fetchone()[0]
    if "alias_id" in columns:
        alias_columns = _table_columns(env, "mail_alias")
        alias_values = [
            sql.SQL("NULL")
            if name in ("alias_name", "alias_full_name")
            else sql.Literal(clone_id)
            if name == "alias_parent_thread_id"
            else sql.Literal(str({"job_id": clone_id, "company_id": company_id}))
            if name == "alias_defaults"
            else sql.Identifier(name)
            for name in alias_columns
        ]
        env.cr.execute(
            sql.SQL(
                "INSERT INTO mail_alias ({columns}) SELECT {values} "
                "FROM mail_alias WHERE id = "
                "(SELECT alias_id FROM hr_job WHERE id = %s) RETURNING id"
            ).format(
                columns=sql.SQL(", ").join(map(sql.Identifier, alias_columns)),
                values=sql.SQL(", ").join(alias_values),
            ),
            (job_id,),
        )
        row = env.cr.fetchone()
        env.cr.execute(
            "UPDATE hr_job SET alias_id = %s WHERE id = %s",
            (row and row[0], clone_id),
        )
    _hr_job_copy_relations(env, references, job_id, clone_id)
    return clone_id


def _hr_job_repoint(env, references, job_id, target_id, company_id=None):
    """
    Point the many2one fields from a job to another one, only for the records of
    a company if given, else for all the records left
    """
    for table, column, has_id, has_company in references:
        if not has_id or (company_id and not has_company):
            continue
        query = sql.SQL("UPDATE {table} SET {column} = %s WHERE {column} = %s").format(
            table=sql.Identifier(table), column=sql.Identifier(column)
        )
        params = [target_id, job_id]
        if company_id:
            query += sql.SQL(" AND company_id = %s")
            params.append(company_id)
            openupgrade.logged_query(env.cr, query, tuple(params))
            continue
        try:
            with env.cr.savepoint():
                openupgrade.logged_query(env.cr, query, tuple(params))
        except psycopg2.IntegrityError:
            _logger.info(
                "Rows of %s pointing to the job %s are duplicates in the job %s",
                table,
                job_id,
                target_id,
            )


def _hr_job_merge(env, references, job_id, target_id):
    """
    Move everything left on a job to another one and delete it
    """
    _hr_job_copy_relations(env, references, job_id, target_id)
    _hr_job_repoint(env, references, job_id, target_id)
    for table, model_column in (
        ("mail_message", "model"),
        ("ir_attachment", "res_model"),
        ("mail_activity", "res_model"),
    ):
        openupgrade.logged_query(
            env.cr,
            sql.SQL(
                "UPDATE {table} SET res_id = %s "
                "WHERE {model_column} = 'hr.job' AND res_id = %s"
            ).format(
                table=sql.Identifier(table),
                model_column=sql.Identifier(model_column),
            ),
            (target_id, job_id),
        )
    openupgrade.logged_query(
        env.cr,
        "DELETE FROM mail_followers WHERE res_model = 'hr.job' AND res_id = %s",
        (job_id,),
    )
    alias_id = None
    if "alias_id" in _table_columns(env, "hr_job"):
        env.cr.execute("SELECT alias_id FROM hr_job WHERE id = %s", (job_id,))
        alias_id = env.cr.fetchone()[0]
    openupgrade.logged_query(env.cr, "DELETE FROM hr_job WHERE id = %s", (job_id,))
    if alias_id:
        openupgrade.logged_query(
            env.cr, "DELETE FROM mail_alias WHERE id = %s", (alias_id,)
        )
    openupgrade.logged_query(
        env.cr,
        "DELETE FROM ir_model_data WHERE model = 'hr.job' AND res_id = %s",
        (job_id,),
    )


def hr_job_company_id(env):
    """
    hr.job#company_id is required now. A job without company goes to the company
    of its department, else to the company that uses it most, else to the main
    company, merging it into the job with the same name and department there.
    The other companies that use it get their own copy without department, so
    that no version or applicant points to a job of another company
    """
    references = _hr_job_references(env)
    usage_queries = [
        sql.SQL(
            "SELECT {column} AS job_id, company_id FROM {table} "
            "WHERE company_id IS NOT NULL"
        ).format(table=sql.Identifier(table), column=sql.Identifier(column))
        for table, column, has_id, has_company in references
        if has_id and has_company
    ]
    env.cr.execute(
        "SELECT id FROM res_company ORDER BY parent_id IS NOT NULL, id LIMIT 1"
    )
    main_company_id = env.cr.fetchone()[0]
    env.cr.execute(
        """
        SELECT hr_job.id, hr_job.department_id, hr_department.company_id
        FROM hr_job
        LEFT JOIN hr_department ON hr_department.id = hr_job.department_id
        WHERE hr_job.company_id IS NULL
        ORDER BY hr_job.id
        """
    )
    for job_id, department_id, department_company_id in env.cr.fetchall():
        company_ids = []
        if usage_queries:
            env.cr.execute(
                sql.SQL(
                    "SELECT company_id FROM ({usage}) job_usage WHERE job_id = %s "
                    "GROUP BY company_id ORDER BY count(*) DESC, company_id"
                ).format(usage=sql.SQL(" UNION ALL ").join(usage_queries)),
                (job_id,),
            )
            company_ids = [row[0] for row in env.cr.fetchall()]
        primary_id = department_company_id or (
            company_ids[0] if company_ids else main_company_id
        )
        for company_id in company_ids:
            if company_id == primary_id:
                continue
            env.cr.execute(
                """
                SELECT hr_job.id
                FROM hr_job, hr_job job
                WHERE job.id = %s AND hr_job.name = job.name
                AND hr_job.company_id = %s AND hr_job.department_id IS NULL
                ORDER BY hr_job.id
                LIMIT 1
                """,
                (job_id, company_id),
            )
            row = env.cr.fetchone()
            if row:
                target_id = row[0]
                _hr_job_copy_relations(env, references, job_id, target_id)
            else:
                target_id = _hr_job_clone(env, references, job_id, company_id)
            _hr_job_repoint(env, references, job_id, target_id, company_id)
        env.cr.execute(
            """
            SELECT hr_job.id
            FROM hr_job, hr_job job
            WHERE job.id = %s AND hr_job.name = job.name
            AND hr_job.company_id = %s AND hr_job.department_id = %s
            ORDER BY hr_job.id
            LIMIT 1
            """,
            (job_id, primary_id, department_id),
        )
        row = env.cr.fetchone()
        if row:
            _hr_job_merge(env, references, job_id, row[0])
        else:
            openupgrade.logged_query(
                env.cr,
                "UPDATE hr_job SET company_id = %s WHERE id = %s",
                (primary_id, job_id),
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

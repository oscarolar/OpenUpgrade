# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_employee_type_xmlids = {
    "employee": "hr.contract_type_employee",
    "student": "hr.contract_type_student",
    "trainee": "hr.contract_type_intern",
}

_employee_type_names = {
    "employee": "Employee",
    "student": "Student",
    "trainee": "Intern",
    "worker": "Worker",
    "contractor": "Contractor",
    "freelance": "Freelancer",
}

_obsolete_noupdate_xmlids = [
    "hr.contract_type_full_time",
    "hr.contract_type_part_time",
    "hr.contract_type_permanent",
    "hr.contract_type_statutory",
    "hr.contract_type_temporary",
]


def hr_version_employee_type_id(env):
    """
    Fill hr.version#employee_type_id from the removed selection employee_type for
    versions without contract type, creating the types that don't exist in v20.
    The contract type wins when both are set, those versions are reported
    """
    env.cr.execute(
        """
        SELECT employee_type, count(*)
        FROM hr_version
        WHERE employee_type_id IS NOT NULL
        AND employee_type IS NOT NULL AND employee_type != 'employee'
        GROUP BY employee_type
        ORDER BY employee_type
        """
    )
    for employee_type, count in env.cr.fetchall():
        openupgrade.message(
            env.cr,
            "hr",
            "hr_version",
            "employee_type_id",
            "%s versions keep their contract type as employee type, their former "
            "employee type '%s' stays only in the column employee_type",
            count,
            employee_type,
        )
    env.cr.execute(
        """
        SELECT DISTINCT employee_type
        FROM hr_version
        WHERE employee_type_id IS NULL AND employee_type IS NOT NULL
        """
    )
    for (employee_type,) in env.cr.fetchall():
        if employee_type not in _employee_type_names:
            continue
        type_record = env.ref(
            _employee_type_xmlids.get(employee_type, "hr.no_such_type"),
            raise_if_not_found=False,
        ) or env["hr.employee.type"].create(
            {"name": _employee_type_names[employee_type]}
        )
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE hr_version
            SET employee_type_id = %s
            WHERE employee_type_id IS NULL AND employee_type = %s
            """,
            (type_record.id, employee_type),
        )


def hr_version_fixed_term(env):
    """
    Versions with a contract end date are fixed term contracts, unless the end date
    is the departure date that the departure wizard wrote on the contract
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_version
        SET fixed_term = TRUE
        WHERE contract_date_end IS NOT NULL
        AND contract_date_end IS DISTINCT FROM departure_date
        """,
    )


def hr_employee_from_version(env):
    """
    hr.employee#additional_note and #contract_template_id are stored on the
    employee now, take them from the current version
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_employee
        SET
            additional_note = hr_version.additional_note,
            contract_template_id = hr_version.contract_template_id
        FROM hr_version
        WHERE hr_version.id = hr_employee.current_version_id
        AND (
            hr_version.additional_note IS NOT NULL
            OR hr_version.contract_template_id IS NOT NULL
        )
        """,
    )


def hr_employee_departure(env):
    """
    Create hr.employee.departure records from the departure fields of the versions.
    The ones of archived employees are created as already applied, the cron must not
    archive anything because of the migration. Active employees only get a planned
    departure when the date is in the future, the others are reported
    """
    env.cr.execute(
        """
        SELECT DISTINCT hr_employee.id, hr_employee.name
        FROM hr_version
        JOIN hr_employee ON hr_employee.id = hr_version.employee_id
        WHERE hr_version.departure_reason_id IS NOT NULL
        AND hr_employee.active
        AND COALESCE(hr_version.departure_date, CURRENT_DATE) <= CURRENT_DATE
        ORDER BY hr_employee.id
        """
    )
    for employee_id, name in env.cr.fetchall():
        openupgrade.message(
            env.cr,
            "hr",
            "hr_employee_departure",
            "employee_id",
            "The active employee %s (id %s) has a departure reason with a date that "
            "is not in the future: no departure is created, the values stay in the "
            "columns departure_reason_id, departure_date and departure_description "
            "of hr_version",
            name,
            employee_id,
        )
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO hr_employee_departure (
            employee_id, departure_reason_id, departure_description,
            dismissal_date, departure_date, action_date, apply_date,
            create_uid, create_date, write_uid, write_date
        )
        SELECT DISTINCT ON (hr_version.employee_id)
            hr_version.employee_id,
            hr_version.departure_reason_id,
            hr_version.departure_description,
            COALESCE(hr_version.departure_date, hr_version.write_date::date),
            COALESCE(hr_version.departure_date, hr_version.write_date::date),
            COALESCE(hr_version.departure_date, hr_version.write_date::date)
                + interval '1 day',
            CASE WHEN NOT hr_employee.active THEN
                COALESCE(hr_version.departure_date, hr_version.write_date::date)
            END,
            hr_version.write_uid, hr_version.write_date,
            hr_version.write_uid, hr_version.write_date
        FROM hr_version
        JOIN hr_employee ON hr_employee.id = hr_version.employee_id
        WHERE hr_version.departure_reason_id IS NOT NULL
        AND (NOT hr_employee.active OR hr_version.departure_date > CURRENT_DATE)
        ORDER BY hr_version.employee_id, hr_version.date_version DESC
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_version
        SET departure_id = hr_employee_departure.id
        FROM hr_employee_departure
        WHERE hr_employee_departure.employee_id = hr_version.employee_id
        AND hr_version.departure_reason_id IS NOT NULL
        """,
    )


def hr_job_recruiter_id(env):
    """
    hr.job#user_id is replaced by #recruiter_id, pointing to the employee of the
    user in the company of the job. Jobs whose user has no employee there are left
    without recruiter and reported
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_job
        SET recruiter_id = (
            SELECT hr_employee.id
            FROM hr_employee
            WHERE hr_employee.user_id = hr_job.user_id
            AND hr_employee.company_id = hr_job.company_id
            ORDER BY hr_employee.active DESC, hr_employee.id
            LIMIT 1
        )
        WHERE user_id IS NOT NULL
        """,
    )
    env.cr.execute(
        """
        SELECT hr_job.id, hr_job.name->>'en_US', res_users.login
        FROM hr_job
        JOIN res_users ON res_users.id = hr_job.user_id
        WHERE hr_job.recruiter_id IS NULL
        ORDER BY hr_job.id
        """
    )
    for job_id, name, login in env.cr.fetchall():
        openupgrade.message(
            env.cr,
            "hr",
            "hr_job",
            "recruiter_id",
            "The job %s (id %s) is left without recruiter: its user %s has no "
            "employee in the company of the job. The user stays in the column "
            "user_id",
            name,
            job_id,
            login,
        )


def delete_unreferenced_records(env, xmlids):
    """
    Delete obsolete noupdate records only when no row points to them, as their
    foreign keys set null on delete
    """
    for xmlid in xmlids:
        record = env.ref(xmlid, raise_if_not_found=False)
        if not record:
            continue
        env.cr.execute(
            """
            SELECT pg_class.relname, pg_attribute.attname
            FROM pg_constraint
            JOIN pg_class ON pg_class.oid = pg_constraint.conrelid
            JOIN pg_attribute
                ON pg_attribute.attrelid = pg_constraint.conrelid
                AND pg_attribute.attnum = pg_constraint.conkey[1]
            WHERE pg_constraint.contype = 'f'
            AND pg_constraint.confrelid = %s::regclass
            """,
            (record._table,),
        )
        referenced = False
        for table, column in env.cr.fetchall():
            env.cr.execute(
                f'SELECT 1 FROM "{table}" WHERE "{column}" = %s LIMIT 1',
                (record.id,),
            )
            if env.cr.rowcount:
                referenced = True
                break
        if not referenced:
            openupgrade.delete_records_safely_by_xml_id(env, [xmlid])


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "hr", "20.0.1.1/noupdate_changes.xml")
    hr_version_employee_type_id(env)
    hr_version_fixed_term(env)
    hr_employee_from_version(env)
    hr_employee_departure(env)
    hr_job_recruiter_id(env)
    delete_unreferenced_records(env, _obsolete_noupdate_xmlids)

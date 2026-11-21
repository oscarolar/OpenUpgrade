# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_employee_type_xmlids = {
    "employee": "hr.contract_type_employee",
    "student": "hr.contract_type_student",
    "trainee": "hr.contract_type_intern",
}

_employee_type_names = {
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
    versions without contract type, creating the types that don't exist in v20
    """
    env.cr.execute(
        """
        SELECT DISTINCT employee_type
        FROM hr_version
        WHERE employee_type_id IS NULL AND employee_type IS NOT NULL
        """
    )
    for (employee_type,) in env.cr.fetchall():
        if employee_type in _employee_type_xmlids:
            type_record = env.ref(
                _employee_type_xmlids[employee_type], raise_if_not_found=False
            )
        elif employee_type in _employee_type_names:
            type_record = env["hr.employee.type"].create(
                {"name": _employee_type_names[employee_type]}
            )
        else:
            continue
        if not type_record:
            continue
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
    Versions with a contract end date are fixed term contracts
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_version
        SET fixed_term = TRUE
        WHERE contract_date_end IS NOT NULL
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
    Create hr.employee.departure records from the departure fields of the versions
    of archived employees. They are created as already applied, the cron must not
    archive anything because of the migration
    """
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
            COALESCE(hr_version.departure_date, hr_version.write_date::date),
            hr_version.write_uid, hr_version.write_date,
            hr_version.write_uid, hr_version.write_date
        FROM hr_version
        JOIN hr_employee ON hr_employee.id = hr_version.employee_id
        WHERE hr_version.departure_reason_id IS NOT NULL
        AND NOT hr_employee.active
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
    user, preferably the one of the company of the job
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_job
        SET recruiter_id = (
            SELECT hr_employee.id
            FROM hr_employee
            WHERE hr_employee.user_id = hr_job.user_id
            ORDER BY
                hr_employee.company_id = hr_job.company_id DESC,
                hr_employee.active DESC,
                hr_employee.id
            LIMIT 1
        )
        WHERE user_id IS NOT NULL
        """,
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

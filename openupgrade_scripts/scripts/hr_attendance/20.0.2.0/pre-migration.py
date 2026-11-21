# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_added_columns = [
    ("res.company", "attendance_validation", "selection", "no_validation"),
    ("res.company", "attendance_work_entry_type_id", "many2one"),
    (
        "hr.attendance",
        "break_duration",
        "float",
        None,
        "hr_attendance",
        "double precision",
    ),
    ("hr.attendance", "day_of_date", "selection"),
    ("hr.attendance", "state", "selection", "validated"),
    ("hr.attendance", "work_entry_type_id", "many2one"),
]


def res_company_attendance_validation(env):
    """
    Companies where a manager approved the extra hours now approve the attendances
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_company
        SET attendance_validation='manual_validation'
        WHERE attendance_overtime_validation='by_manager'
        """,
    )


def res_company_attendance_work_entry_type_id(env):
    """
    Fill res.company#attendance_work_entry_type_id as its compute method does: the
    attendance type of the country of the company, or the generic one
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_company
        SET attendance_work_entry_type_id=COALESCE(
            (
                SELECT MIN(hr_work_entry_type.id)
                FROM hr_work_entry_type
                JOIN res_partner
                ON res_partner.country_id=hr_work_entry_type.country_id
                WHERE
                    res_partner.id=res_company.partner_id
                AND hr_work_entry_type.count_as='working_time'
                AND hr_work_entry_type.code='002.00'
            ),
            (
                SELECT res_id
                FROM ir_model_data
                WHERE
                    module='hr_work_entry'
                AND name='generic_work_entry_type_attendance'
            )
        )
        """,
    )


def hr_attendance_work_entry_type_id(env):
    """
    Fill hr.attendance#work_entry_type_id with the attendance type of the company of
    the employee
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_attendance
        SET work_entry_type_id=res_company.attendance_work_entry_type_id
        FROM hr_employee
        JOIN res_company
        ON res_company.id=hr_employee.company_id
        WHERE hr_employee.id=hr_attendance.employee_id
        """,
    )


def hr_attendance_state(env):
    """
    Attendances were always valid in v19 and only their extra hours could wait for
    approval: leave in draft the ones a manager still has to look at
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_attendance
        SET state='draft'
        FROM hr_employee
        JOIN res_company
        ON res_company.id=hr_employee.company_id
        WHERE
            hr_employee.id=hr_attendance.employee_id
        AND res_company.attendance_validation='manual_validation'
        AND (
            hr_attendance.overtime_status='to_approve'
            OR hr_attendance.check_out IS NULL
        )
        """,
    )


def hr_attendance_day_of_date(env):
    """
    Precompute hr.attendance#day_of_date
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_attendance
        SET day_of_date=(EXTRACT(ISODOW FROM date)::int - 1)::varchar
        WHERE date IS NOT NULL
        """,
    )


def hr_attendance_break_duration(env):
    """
    v19 subtracted the lunch of the schedule from worked_hours, v20 only subtracts
    break_duration: store that difference as break
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_attendance
        SET break_duration=ROUND(
            (
                EXTRACT(EPOCH FROM (check_out - check_in)) / 3600.0 - worked_hours
            )::numeric,
            4
        )
        WHERE
            check_out IS NOT NULL
        AND worked_hours IS NOT NULL
        AND EXTRACT(EPOCH FROM (check_out - check_in)) / 3600.0 - worked_hours
            > 0.001
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.add_columns(env, _added_columns)
    res_company_attendance_validation(env)
    res_company_attendance_work_entry_type_id(env)
    hr_attendance_work_entry_type_id(env)
    hr_attendance_state(env)
    hr_attendance_day_of_date(env)
    hr_attendance_break_duration(env)

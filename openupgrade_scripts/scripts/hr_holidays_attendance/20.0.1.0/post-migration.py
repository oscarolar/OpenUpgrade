# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def hr_leave_allocation_from_overtime(env):
    """
    Extra hours are not deducted from the time off of a time type anymore, the
    time rules allocate them instead. Turn the time types that deducted extra
    hours without allocation into types requiring one, and give every employee a
    validated allocation that leaves the same balance as in v19: approved
    compensable extra hours, minus the time off taken on those types, minus the
    allocations already taken from the extra hours
    """
    env.cr.execute(
        """
        SELECT hr_work_entry_type.id
        FROM hr_work_entry_type
        JOIN hr_leave_type
            ON hr_leave_type.id
            = hr_work_entry_type.openupgrade_legacy_20_0_leave_type_id
        WHERE hr_leave_type.overtime_deductible
        AND hr_leave_type.requires_allocation IS NOT TRUE
        ORDER BY hr_work_entry_type.id
        """
    )
    type_ids = [row[0] for row in env.cr.fetchall()]
    if not type_ids:
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_work_entry_type
        SET requires_allocation = TRUE
        WHERE id IN %s
        """,
        (tuple(type_ids),),
    )
    env["hr.work.entry.type"].invalidate_model(["requires_allocation"])
    env.cr.execute(
        """
        WITH deductible_type AS (
            SELECT hr_work_entry_type.id
            FROM hr_work_entry_type
            JOIN hr_leave_type
                ON hr_leave_type.id
                = hr_work_entry_type.openupgrade_legacy_20_0_leave_type_id
            WHERE hr_leave_type.overtime_deductible
        ),
        overtime AS (
            SELECT employee_id, SUM(manual_duration) AS hours, MIN(date) AS date
            FROM hr_attendance_overtime_line
            WHERE status = 'approved' AND compensable_as_leave
            GROUP BY employee_id
        ),
        leave AS (
            SELECT
                employee_id,
                work_entry_type_id,
                SUM(number_of_hours) AS hours,
                MIN(date_from)::date AS date
            FROM hr_leave
            WHERE work_entry_type_id IN %(type_ids)s
            AND state NOT IN ('refuse', 'cancel')
            GROUP BY employee_id, work_entry_type_id
        ),
        employee AS (
            SELECT
                hr_employee.id AS employee_id,
                (
                    SELECT hr_work_entry_type.id
                    FROM hr_work_entry_type
                    LEFT JOIN res_company
                        ON res_company.id = hr_employee.company_id
                    LEFT JOIN res_partner
                        ON res_partner.id = res_company.partner_id
                    WHERE hr_work_entry_type.id IN %(type_ids)s
                    ORDER BY
                        hr_work_entry_type.country_id IS NOT DISTINCT FROM
                        res_partner.country_id DESC,
                        hr_work_entry_type.openupgrade_legacy_20_0_leave_type_copy
                        IS TRUE,
                        hr_work_entry_type.id
                    LIMIT 1
                ) AS main_type_id
            FROM hr_employee
            WHERE hr_employee.id IN (
                SELECT employee_id FROM overtime
                UNION
                SELECT employee_id FROM leave
            )
        ),
        allocation AS (
            SELECT
                hr_leave_allocation.employee_id,
                SUM(number_of_hours) AS hours,
                SUM(number_of_hours) FILTER (
                    WHERE work_entry_type_id = employee.main_type_id
                    AND state = 'validate'
                ) AS main_hours
            FROM hr_leave_allocation
            JOIN employee
                ON employee.employee_id = hr_leave_allocation.employee_id
            WHERE work_entry_type_id IN (SELECT id FROM deductible_type)
            AND state IN ('confirm', 'validate', 'validate1')
            GROUP BY hr_leave_allocation.employee_id
        )
        SELECT
            employee.employee_id,
            employee.main_type_id,
            COALESCE(overtime.hours, 0)
            - COALESCE(allocation.hours, 0)
            - COALESCE(allocation.main_hours, 0)
            - COALESCE((
                SELECT SUM(leave.hours) FROM leave
                WHERE leave.employee_id = employee.employee_id
                AND leave.work_entry_type_id != employee.main_type_id
            ), 0),
            LEAST(overtime.date, (
                SELECT MIN(leave.date) FROM leave
                WHERE leave.employee_id = employee.employee_id
            ))
        FROM employee
        LEFT JOIN overtime ON overtime.employee_id = employee.employee_id
        LEFT JOIN allocation ON allocation.employee_id = employee.employee_id
        UNION ALL
        SELECT leave.employee_id, leave.work_entry_type_id, leave.hours, leave.date
        FROM leave
        JOIN employee ON employee.employee_id = leave.employee_id
        WHERE leave.work_entry_type_id != employee.main_type_id
        """,
        {"type_ids": tuple(type_ids)},
    )
    Allocation = env["hr.leave.allocation"].with_context(
        mail_create_nosubscribe=True, mail_create_nolog=True, tracking_disable=True
    )
    allocation_ids = []
    for employee_id, type_id, hours, date_from in env.cr.fetchall():
        if not hours or hours <= 0:
            continue
        allocation = Allocation.create(
            {
                "name": "Extra hours before the migration to v20",
                "employee_id": employee_id,
                "work_entry_type_id": type_id,
                "date_from": date_from,
                "number_of_days": 0,
            }
        )
        allocation.number_of_hours = hours
        allocation_ids.append(allocation.id)
    if not allocation_ids:
        return
    env["hr.leave.allocation"].flush_model()
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_leave_allocation
        SET state = 'validate', approver_id = NULL
        WHERE id IN %s
        """,
        (tuple(allocation_ids),),
    )
    env["hr.leave.allocation"].invalidate_model()


@openupgrade.migrate()
def migrate(env, version):
    hr_leave_allocation_from_overtime(env)

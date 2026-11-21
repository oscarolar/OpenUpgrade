from datetime import date

env = locals().get("env")

extra_hours = env.ref("hr_holidays.holiday_status_extra_hours")
employee = env["hr.employee"].create(
    {
        "name": "OpenUpgrade v20 extra hours",
        "company_id": env.ref("base.main_company").id,
    }
)
env["hr.attendance.overtime.line"].create(
    [
        {
            "employee_id": employee.id,
            "date": "2026-01-05",
            "duration": 10,
            "manual_duration": 10,
            "status": "approved",
            "compensable_as_leave": True,
        },
        {
            "employee_id": employee.id,
            "date": "2026-01-06",
            "duration": 5,
            "manual_duration": 5,
            "status": "to_approve",
            "compensable_as_leave": True,
        },
        {
            "employee_id": employee.id,
            "date": "2026-01-07",
            "duration": 3,
            "manual_duration": 3,
            "status": "approved",
            "compensable_as_leave": False,
        },
    ]
)
day = date(2026, 1, 12)
env["hr.leave"].with_context(leave_skip_state_check=True).create(
    {
        "name": "OpenUpgrade v20 extra hours leave",
        "employee_id": employee.id,
        "holiday_status_id": extra_hours.id,
        "request_date_from": day,
        "request_date_to": day,
        "request_unit_hours": True,
        "request_hour_from": 8,
        "request_hour_to": 10,
    }
)
env.cr.commit()

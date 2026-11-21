env = locals().get("env")
company_be = env["res.company"].create(
    {"name": "OpenUpgrade v20 BE company", "country_id": env.ref("base.be").id}
)
company_none = env["res.company"].create({"name": "OpenUpgrade v20 stateless company"})
leave_type = env["hr.leave.type"].create(
    {
        "name": "OpenUpgrade v20 shared time off",
        "requires_allocation": True,
        "request_unit": "day",
        "country_id": False,
        "company_id": False,
    }
)
for name, company in (
    ("main", env.ref("base.main_company")),
    ("be", company_be),
    ("stateless", company_none),
):
    employee = env["hr.employee"].create(
        {"name": f"OpenUpgrade v20 time off {name}", "company_id": company.id}
    )
    allocation = env["hr.leave.allocation"].create(
        {
            "name": f"OpenUpgrade v20 allocation {name}",
            "employee_id": employee.id,
            "holiday_status_id": leave_type.id,
            "number_of_days": 5,
            "date_from": "2026-01-01",
        }
    )
    if allocation.state != "validate":
        allocation.action_approve()
env.cr.commit()

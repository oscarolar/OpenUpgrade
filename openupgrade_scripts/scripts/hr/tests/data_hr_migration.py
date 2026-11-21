env = locals().get("env")
company = env.ref("base.main_company")
user = env["res.users"].create(
    {
        "name": "OpenUpgrade v20 hr recruiter",
        "login": "ou20_hr_recruiter",
        "company_id": company.id,
        "company_ids": [(6, 0, company.ids)],
    }
)
env["hr.employee"].create(
    {
        "name": "OpenUpgrade v20 recruiter",
        "user_id": user.id,
        "company_id": company.id,
    }
)
env["hr.employee"].create(
    {
        "name": "OpenUpgrade v20 worker",
        "company_id": company.id,
        "employee_type": "worker",
        "additional_note": "OpenUpgrade v20 note",
        "contract_date_start": "2025-01-01",
        "contract_date_end": "2025-12-31",
    }
)
env["hr.employee"].create(
    {
        "name": "OpenUpgrade v20 student",
        "company_id": company.id,
        "employee_type": "student",
    }
)
env["hr.employee"].create(
    {
        "name": "OpenUpgrade v20 permanent",
        "company_id": company.id,
        "contract_type_id": env.ref("hr.contract_type_permanent").id,
    }
)
env["hr.employee"].create(
    {
        "name": "OpenUpgrade v20 flexible",
        "company_id": company.id,
        "resource_calendar_id": False,
        "tz": "America/Mexico_City",
    }
)
departed = env["hr.employee"].create(
    {
        "name": "OpenUpgrade v20 departed",
        "company_id": company.id,
    }
)
departed.with_context(no_wizard=True).action_archive()
departed.write(
    {
        "departure_reason_id": env.ref("hr.departure_fired").id,
        "departure_date": "2025-06-30",
    }
)
env["hr.job"].create(
    {
        "name": "OpenUpgrade v20 job",
        "company_id": False,
        "user_id": user.id,
    }
)
plan = env["mail.activity.plan"].create(
    {
        "name": "OpenUpgrade v20 plan",
        "res_model": "hr.employee",
    }
)
env["mail.activity.plan.template"].create(
    {
        "plan_id": plan.id,
        "summary": "OpenUpgrade v20 coach template",
        "activity_type_id": env.ref("mail.mail_activity_data_todo").id,
        "responsible_type": "coach",
    }
)
env.cr.commit()

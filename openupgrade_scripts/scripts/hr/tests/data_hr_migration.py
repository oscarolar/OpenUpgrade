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
        "contract_date_start": "2025-01-01",
        "contract_date_end": "2025-06-30",
    }
)
env["hr.employee"].create(
    {
        "name": "OpenUpgrade v20 leaving",
        "company_id": company.id,
        "departure_reason_id": env.ref("hr.departure_resigned").id,
        "departure_date": "2099-01-01",
    }
)
env["hr.employee"].create(
    {
        "name": "OpenUpgrade v20 stayed",
        "company_id": company.id,
        "departure_reason_id": env.ref("hr.departure_resigned").id,
        "departure_date": "2020-01-01",
    }
)
company2 = env["res.company"].create({"name": "OpenUpgrade v20 company 2"})
department = env["hr.department"].create(
    {"name": "OpenUpgrade v20 department", "company_id": company.id}
)
env["hr.job"].create(
    {
        "name": "OpenUpgrade v20 duplicated job",
        "company_id": company.id,
        "department_id": department.id,
    }
)
duplicated_job = env["hr.job"].create(
    {
        "name": "OpenUpgrade v20 duplicated job",
        "company_id": False,
        "department_id": department.id,
    }
)
env["hr.employee"].create(
    {
        "name": "OpenUpgrade v20 duplicated job",
        "company_id": company.id,
        "job_id": duplicated_job.id,
    }
)
shared_job = env["hr.job"].create(
    {"name": "OpenUpgrade v20 shared job", "company_id": False}
)
env["hr.employee"].create(
    {
        "name": "OpenUpgrade v20 shared job 1",
        "company_id": company.id,
        "job_id": shared_job.id,
    }
)
env["hr.employee"].create(
    {
        "name": "OpenUpgrade v20 shared job 2",
        "company_id": company2.id,
        "job_id": shared_job.id,
    }
)
env["hr.job"].create(
    {
        "name": "OpenUpgrade v20 job of company 2",
        "company_id": company2.id,
        "user_id": user.id,
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

env = locals().get("env")

recruiter_user = env["res.users"].create(
    {
        "name": "ou19 recruiter",
        "login": "ou19_recruiter",
        "group_ids": [(4, env.ref("hr_recruitment.group_hr_recruitment_user").id)],
    }
)
env["hr.employee"].create(
    {
        "name": "ou19 recruiter",
        "user_id": recruiter_user.id,
        "company_id": env.company.id,
    }
)
job = env["hr.job"].create(
    {
        "name": "ou19 job",
        "company_id": env.company.id,
        "user_id": recruiter_user.id,
        "applicant_properties_definition": [
            {"name": "ou19field", "string": "Ou19field", "type": "char"},
        ],
    }
)
job.favorite_user_ids = recruiter_user
env["hr.applicant"].create(
    {
        "partner_name": "ou19 applicant",
        "job_id": job.id,
        "user_id": recruiter_user.id,
        "applicant_properties": {"ou19field": "ou19 value"},
    }
)
company2 = env["res.company"].create({"name": "ou19 recruitment company 2"})
job2 = env["hr.job"].create(
    {
        "name": "ou19 job of company 2",
        "company_id": company2.id,
        "user_id": recruiter_user.id,
    }
)
job2.favorite_user_ids = recruiter_user
env["hr.applicant"].create(
    {
        "partner_name": "ou19 applicant of company 2",
        "job_id": job2.id,
        "company_id": company2.id,
        "user_id": recruiter_user.id,
    }
)

env.cr.commit()

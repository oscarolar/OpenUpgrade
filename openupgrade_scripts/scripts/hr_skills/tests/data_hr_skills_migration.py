import base64

env = locals().get("env")
certification = env.ref("hr_skills.mail_activity_data_upload_certification")
plan = env["mail.activity.plan"].create(
    {"name": "OpenUpgrade v20 skills plan", "res_model": "hr.employee"}
)
env["mail.activity.plan.template"].create(
    {
        "plan_id": plan.id,
        "summary": "OpenUpgrade v20 certification template",
        "activity_type_id": certification.id,
    }
)
env["ir.actions.server"].create(
    {
        "name": "OpenUpgrade v20 certification action",
        "model_id": env.ref("hr.model_hr_employee").id,
        "state": "next_activity",
        "activity_type_id": certification.id,
        "activity_summary": "OpenUpgrade v20",
        "activity_user_type": "generic",
        "activity_user_field_name": "user_id",
    }
)
employee = env["hr.employee"].create({"name": "OpenUpgrade v20 certified"})
env["hr.resume.line"].create(
    {
        "employee_id": employee.id,
        "name": "OpenUpgrade v20 resume line",
        "certificate_file": base64.b64encode(b"%PDF-1.4\n%%EOF\n"),
        "certificate_filename": "ou20_certificate.pdf",
    }
)
env.cr.commit()

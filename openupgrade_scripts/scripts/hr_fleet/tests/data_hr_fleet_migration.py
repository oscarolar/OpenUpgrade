env = locals().get("env")
plan = env["mail.activity.plan"].create(
    {"name": "OpenUpgrade v20 fleet plan", "res_model": "hr.employee"}
)
env["mail.activity.plan.template"].create(
    {
        "plan_id": plan.id,
        "summary": "OpenUpgrade v20 fleet template",
        "responsible_type": "fleet_manager",
    }
)
env.cr.commit()

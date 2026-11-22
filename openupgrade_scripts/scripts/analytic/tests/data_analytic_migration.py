env = locals().get("env")

env.ref("analytic.analytic_plan_projects").name = "OU Departments"

env.cr.commit()

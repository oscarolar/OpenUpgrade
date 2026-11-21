env = locals().get("env")
partners = env["res.partner"]
for name in ("limited", "collaborator", "follower"):
    user = env["res.users"].create(
        {
            "name": f"OpenUpgrade v20 project {name}",
            "login": f"ou20_project_{name}",
            "group_ids": [(6, 0, env.ref("base.group_portal").ids)],
        }
    )
    partners += user.partner_id
limited, collaborator, follower = partners
project = env["project.project"].create(
    {
        "name": "OpenUpgrade v20 shared project",
        "privacy_visibility": "portal",
    }
)
env["project.collaborator"].create(
    [
        {
            "project_id": project.id,
            "partner_id": limited.id,
            "limited_access": True,
        },
        {
            "project_id": project.id,
            "partner_id": collaborator.id,
            "limited_access": False,
        },
    ]
)
project.message_subscribe(partner_ids=follower.ids)
stages = env["project.task.type"].create(
    [
        {"name": "OpenUpgrade v20 stage 1", "project_ids": [(4, project.id)]},
        {"name": "OpenUpgrade v20 stage 2", "project_ids": [(4, project.id)]},
    ]
)
task = env["project.task"].create(
    {
        "name": "OpenUpgrade v20 followed task",
        "project_id": project.id,
        "stage_id": stages[0].id,
    }
)
task.message_subscribe(partner_ids=(limited + follower).ids)
env.flush_all()
env.cr.precommit.run()
task.stage_id = stages[1]
env.cr.commit()

env = locals().get("env")
test_user = env["res.users"].search([("login", "=", "test_user_v19")])
Channel = env["discuss.channel"].with_user(test_user)
Channel.search([("name", "=", "OpenUpgrade v20 test channel")]) or Channel.create(
    {
        "name": "OpenUpgrade v20 test channel",
    }
)
Template = env["mail.template"]
test_template = Template.search([("name", "=", "OU20 template")]) or Template.create(
    {
        "name": "OU20 template",
        "model_id": env.ref("base.model_res_partner").id,
        "subject": "OU20 subject",
        "body_html": "<p>OU20 body</p>",
        "email_to": "ou20@example.com",
    }
)
Action = env["ir.actions.server"]
Action.search([("name", "=", "OU20 note")]) or Action.create(
    {
        "name": "OU20 note",
        "model_id": env.ref("base.model_res_partner").id,
        "state": "mail_post",
        "template_id": test_template.id,
        "mail_post_method": "note",
    }
)
Action.search([("name", "=", "OU20 email")]) or Action.create(
    {
        "name": "OU20 email",
        "model_id": env.ref("base.model_res_partner").id,
        "state": "mail_post",
        "template_id": test_template.id,
        "mail_post_method": "email",
    }
)
env.cr.commit()

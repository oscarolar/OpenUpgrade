env = locals().get("env")
test_user = env["res.users"].search([("login", "=", "test_user_v19")])
Channel = env["discuss.channel"].with_user(test_user)
Channel.search([("name", "=", "OpenUpgrade v20 test channel")]) or Channel.create(
    {
        "name": "OpenUpgrade v20 test channel",
    }
)
env.cr.commit()

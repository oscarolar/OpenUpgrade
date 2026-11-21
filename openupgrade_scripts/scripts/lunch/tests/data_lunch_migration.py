env = locals().get("env")
partner = env["res.partner"].create({"name": "OpenUpgrade v20 lunch vendor"})
env["lunch.supplier"].create(
    {
        "partner_id": partner.id,
        "send_by": "mail",
        "automatic_email_time": 3.5,
        "moment": "pm",
    }
)
env["lunch.alert"].create(
    {
        "name": "OpenUpgrade v20 alert",
        "message": "<p>OpenUpgrade v20</p>",
        "notification_time": 1.0,
        "notification_moment": "pm",
    }
)
env["lunch.alert"].create(
    {
        "name": "OpenUpgrade v20 morning alert",
        "message": "<p>OpenUpgrade v20</p>",
        "notification_time": 9.0,
        "notification_moment": "am",
    }
)
env.cr.commit()

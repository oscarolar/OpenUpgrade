env = locals().get("env")
Message = env["mail.message"]
Message.search([("subject", "=", "OpenUpgrade v20 tracking")]) or Message.create(
    {
        "model": "res.partner",
        "res_id": env.ref("base.main_partner").id,
        "subject": "OpenUpgrade v20 tracking",
        "message_type": "notification",
        "tracking_value_ids": [
            (
                0,
                0,
                {
                    "field_id": env["ir.model.fields"]._get("res.partner", "email").id,
                    "old_value_char": "old@example.com",
                    "new_value_char": "<new>@example.com",
                },
            ),
            (
                0,
                0,
                {
                    "field_id": env["ir.model.fields"]._get("res.partner", "active").id,
                    "old_value_integer": 0,
                    "new_value_integer": 1,
                },
            ),
            (
                0,
                0,
                {
                    "field_id": env["ir.model.fields"]
                    ._get("res.partner", "signup_type")
                    .id,
                    "old_value_char": "restricted old",
                    "new_value_char": "restricted new",
                },
            ),
        ],
    }
)
env.cr.commit()

env = locals().get("env")
mailing = env["mailing.mailing"].create(
    {
        "subject": "OpenUpgrade v20 test mailing",
        "mailing_model_id": env["ir.model"]._get_id("res.partner"),
    }
)
env["crm.lead"].create(
    {"name": "OpenUpgrade v20 test mailing lead", "source_id": mailing.source_id.id}
)
env.cr.commit()

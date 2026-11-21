import base64

env = locals().get("env")
Request = env["maintenance.request"]
Request.create(
    {
        "name": "OpenUpgrade v20 pdf",
        "instruction_type": "pdf",
        "instruction_pdf": base64.b64encode(b"%PDF-1.4\n%%EOF\n"),
        "instruction_text": "<p>OpenUpgrade v20 hidden text</p>",
    }
)
Request.create(
    {
        "name": "OpenUpgrade v20 google slide",
        "instruction_type": "google_slide",
        "instruction_google_slide": " https://docs.google.com/x?a=1&b=<2> ",
    }
)
Request.create(
    {
        "name": "OpenUpgrade v20 bad google slide",
        "instruction_type": "google_slide",
        "instruction_google_slide": "javascript:alert(1)",
    }
)
done_stage = env["maintenance.stage"].search([("done", "=", True)], limit=1)
Request.create(
    {
        "name": "OpenUpgrade v20 archived done",
        "stage_id": done_stage.id,
    }
).archive_equipment_request()
Request.create(
    {
        "name": "OpenUpgrade v20 done",
        "stage_id": done_stage.id,
    }
)
env.cr.commit()

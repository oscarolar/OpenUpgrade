env = locals().get("env")
stages = env["crm.stage"].search([], limit=3)
lead = env["crm.lead"].create({"name": "OpenUpgrade v20 test lead"})
lead.stage_id = stages[0]
env.cr.commit()
lead.stage_id = stages[1]
env.cr.commit()
lead.stage_id = stages[2]
env.cr.commit()
env.cr.execute(
    """
    UPDATE crm_lead SET create_date=create_date - interval '3 hours' WHERE id=%s
    """,
    (lead.id,),
)
env.cr.execute(
    """
    WITH ranked AS (
        SELECT
            mail_tracking_value.id,
            row_number() OVER (ORDER BY mail_tracking_value.id DESC) AS position
        FROM mail_tracking_value
        JOIN mail_message ON mail_message.id=mail_tracking_value.mail_message_id
        JOIN ir_model_fields ON ir_model_fields.id=mail_tracking_value.field_id
        WHERE mail_message.model='crm.lead' AND mail_message.res_id=%s
        AND ir_model_fields.name='stage_id'
    )
    UPDATE mail_tracking_value
    SET create_date=mail_tracking_value.create_date
        - (ranked.position - 1) * interval '1 hour'
    FROM ranked
    WHERE ranked.id=mail_tracking_value.id
    """,
    (lead.id,),
)
member = env["crm.team.member"].search([], limit=1)
if member:
    member.write({"assignment_optout": True, "assignment_max": 30})
env.cr.commit()

# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def chatbot_script_step_create_lead_and_forward(env):
    """
    Steps of type create_lead_and_forward were mapped to create_lead, add a
    forward_operator step right after them
    """
    if not openupgrade.column_exists(
        env.cr, "chatbot_script_step", openupgrade.get_legacy_name("step_type")
    ):
        return
    env.cr.execute(
        f"""
        SELECT id
        FROM chatbot_script_step
        WHERE {openupgrade.get_legacy_name("step_type")}='create_lead_and_forward'
        ORDER BY chatbot_script_id, sequence DESC, id DESC
        """
    )
    steps = env["chatbot.script.step"].browse([row[0] for row in env.cr.fetchall()])
    for step in steps:
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE chatbot_script_step
            SET sequence=sequence + 1
            WHERE chatbot_script_id=%(script_id)s
            AND (sequence > %(sequence)s OR (sequence=%(sequence)s AND id > %(id)s))
            """,
            {
                "script_id": step.chatbot_script_id.id,
                "sequence": step.sequence,
                "id": step.id,
            },
        )
        env["chatbot.script.step"].invalidate_model(["sequence"])
        env["chatbot.script.step"].create(
            {
                "chatbot_script_id": step.chatbot_script_id.id,
                "sequence": step.sequence + 1,
                "step_type": "forward_operator",
                "triggering_answer_ids": [(6, 0, step.triggering_answer_ids.ids)],
            }
        )
        env.cr.execute(
            f"""
            UPDATE chatbot_script_step
            SET {openupgrade.get_legacy_name("step_type")}='create_lead'
            WHERE id=%s
            """,
            (step.id,),
        )


def crm_lead_utm_reference(env):
    """
    Leads created by a chatbot had the utm source of the script, which is gone.
    Link them to the script with utm_reference
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE crm_lead
        SET utm_reference='chatbot.script,' || chatbot_script.id
        FROM chatbot_script
        WHERE crm_lead.source_id=chatbot_script.source_id
        AND crm_lead.utm_reference IS NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    chatbot_script_step_create_lead_and_forward(env)
    crm_lead_utm_reference(env)

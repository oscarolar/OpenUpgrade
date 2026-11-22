env = locals().get("env")
partner = env["res.partner"].create({"name": "OU20 Peppol partner"})
moves = env["account.move"].create(
    [
        {
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "ref": f"OU20 Peppol {state}",
        }
        for state in ("skipped", "done", "error")
    ]
)
env.flush_all()
env.cr.execute(
    "UPDATE account_move SET peppol_move_state = substring(ref from 13) WHERE id IN %s",
    [tuple(moves.ids)],
)
env.cr.commit()

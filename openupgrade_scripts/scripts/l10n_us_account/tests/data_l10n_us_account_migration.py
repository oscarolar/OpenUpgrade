env = locals().get("env")
ref = env.ref
intermediary, no_bic = env["res.bank"].create(
    [
        {"name": "OU20 US intermediary", "bic": "OUINUS33XXX"},
        {"name": "OU20 US intermediary without BIC"},
    ]
)
with_bic, without_bic, direct = env["res.bank"].create(
    [
        {
            "name": "OU20 US bank",
            "bic": "OUBKUS44XXX",
            "country": ref("base.us").id,
            "intermediary_bank_id": intermediary.id,
        },
        {
            "name": "OU20 US bank without BIC",
            "country": ref("base.us").id,
            "intermediary_bank_id": no_bic.id,
        },
        {"name": "OU20 US direct bank", "country": ref("base.us").id},
    ]
)
partner = env["res.partner"].create(
    {"name": "OU20 US vendor", "country_id": ref("base.us").id}
)
env["res.partner.bank"].create(
    [
        {"partner_id": partner.id, "acc_number": "OU20-US-1", "bank_id": with_bic.id},
        {"partner_id": partner.id, "acc_number": "OU20-US-2", "bank_id": with_bic.id},
        {
            "partner_id": partner.id,
            "acc_number": "OU20-US-3",
            "bank_id": without_bic.id,
        },
        {"partner_id": partner.id, "acc_number": "OU20-US-4", "bank_id": direct.id},
    ]
)
env.cr.commit()

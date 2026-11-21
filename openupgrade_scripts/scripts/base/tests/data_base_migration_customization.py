env = locals().get("env")
Bank = env["res.bank"]
test_bank = Bank.search([("name", "=", "OpenUpgrade v20 bank")]) or Bank.create(
    {
        "name": "OpenUpgrade v20 bank",
        "bic": "OUPGMXMM",
        "city": "Monterrey",
        "country": env.ref("base.mx").id,
    }
)
Account = env["res.partner.bank"]
Account.search([("acc_number", "=", "OU20 67890")]) or Account.create(
    {
        "partner_id": env.ref("base.main_partner").id,
        "acc_number": "OU20 67890",
        "bank_id": test_bank.id,
    }
)
env.ref("base.res_partner_bank_rule").domain_force = "[('company_id', '=', company_id)]"
env.ref("base.res_currency_rate_rule").active = False
env.ref("base.res_users_rule").groups = env.ref("base.group_system")
env.ref("base.fr").zip_required = False
env.cr.commit()

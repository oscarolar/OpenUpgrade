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
Rule = env["ir.rule"]
Rule.search([("name", "=", "rule with faulty domain")]).unlink()
Rule.search([("name", "=", "OU20 date range")]) or Rule.create(
    {
        "name": "OU20 date range",
        "model_id": env.ref("base.model_ir_sequence_date_range").id,
        "groups": [(6, 0, env.ref("base.group_user").ids)],
        "domain_force": "[('sequence_id', '!=', False)]",
    }
)
Access = env["ir.model.access"]
Access.search([("name", "=", "OU20 device unlink")]) or Access.create(
    {
        "name": "OU20 device unlink",
        "model_id": env.ref("base.model_res_device").id,
        "group_id": env.ref("base.group_user").id,
        "perm_read": False,
        "perm_unlink": True,
    }
)
Rule.search([("name", "=", "OU20 renamed field")]) or Rule.create(
    {
        "name": "OU20 renamed field",
        "model_id": env.ref("base.model_res_partner_bank").id,
        "domain_force": "[('acc_number', '!=', 'OU20 forbidden')]",
    }
)
imported_rule = Rule.search([("name", "=", "OU20 imported")]) or Rule.create(
    {
        "name": "OU20 imported",
        "model_id": env.ref("base.model_res_partner_category").id,
        "domain_force": "[('name', '!=', 'OU20 forbidden')]",
    }
)
ModelData = env["ir.model.data"]
ModelData.search([("module", "=", "__import__")]) or ModelData.create(
    {
        "module": "__import__",
        "name": "ou20_imported_rule",
        "model": "ir.rule",
        "res_id": imported_rule.id,
    }
)
env.ref("base.fr").zip_required = False
env.cr.commit()

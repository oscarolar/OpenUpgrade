env = locals().get("env")
ref = env.ref
company = env["res.company"].search([("name", "=", "OU20 AU")])
if not company:
    company = env["res.company"].create(
        {
            "name": "OU20 AU",
            "country_id": ref("base.au").id,
            "currency_id": ref("base.AUD").id,
        }
    )
    env["account.chart.template"].try_loading("au", company, install_demo=False)
env.user.company_ids |= company
cenv = env(context=dict(env.context, allowed_company_ids=company.ids))
partner = cenv["res.partner"].create(
    {"name": "OU20 AU supplier", "country_id": ref("base.au").id}
)
bank = cenv["res.bank"].create({"name": "OU20 AU bank", "country": ref("base.au").id})
cenv["res.partner.bank"].create(
    [
        {
            "partner_id": partner.id,
            "acc_number": "OU20-AU-1",
            "bank_id": bank.id,
            "aba_bsb": "123-456",
        },
        {
            "partner_id": partner.id,
            "acc_number": "OU20-AU-2",
            "aba_bsb": "654321",
        },
        {
            "partner_id": partner.id,
            "acc_number": "OU20-AU-3",
        },
        {
            "partner_id": company.partner_id.id,
            "acc_number": "OU20-AU-4",
            "bank_id": bank.id,
            "aba_bsb": "111 222",
        },
    ]
)
env.cr.commit()

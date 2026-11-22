env = locals().get("env")
ref = env.ref
company = env["res.company"].search([("name", "=", "OU20 DK")])
if not company:
    company = env["res.company"].create(
        {
            "name": "OU20 DK",
            "country_id": ref("base.dk").id,
            "currency_id": ref("base.DKK").id,
        }
    )
    env["account.chart.template"].try_loading("dk", company, install_demo=False)
env.user.company_ids |= company
main = ref("base.main_company")
oioubl, mixed, other = env["res.partner"].create(
    [
        {"name": "OU20 DK OIOUBL", "country_id": ref("base.dk").id},
        {"name": "OU20 DK mixed", "country_id": ref("base.dk").id},
        {"name": "OU20 DK other", "country_id": ref("base.dk").id},
    ]
)
dk_env = env(context=dict(env.context, allowed_company_ids=company.ids))
(oioubl | mixed).with_env(dk_env).invoice_edi_format = "oioubl_201"
other.with_env(dk_env).invoice_edi_format = "ubl_bis3"
mixed.with_company(main).invoice_edi_format = "ubl_bis3"
env["ir.default"].set(
    "res.partner", "invoice_edi_format_store", "oioubl_201", company_id=company.id
)
env.cr.commit()

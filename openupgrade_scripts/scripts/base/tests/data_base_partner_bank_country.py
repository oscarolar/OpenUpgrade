env = locals().get("env")
ref = env.ref
companies = env["res.company"].search([("name", "like", "OU20 BANK %")])
if not companies:
    for code in ("ca", "jp"):
        company = (
            env["res.company"]
            .with_context(chart_template_load=True)
            .create(
                {
                    "name": f"OU20 BANK {code.upper()}",
                    "country_id": ref(f"base.{code}").id,
                    "currency_id": ref("base.USD").id,
                }
            )
        )
        env["account.chart.template"].try_loading(
            "generic_coa", company, install_demo=False
        )
        companies |= company
company_ca = companies.filtered(lambda company: company.country_id.code == "CA")
company_jp = companies.filtered(lambda company: company.country_id.code == "JP")
env.user.company_ids |= companies
cenv = env(context=dict(env.context, allowed_company_ids=companies.ids))
parent = cenv["res.partner"].create(
    {"name": "OU20 BANK parent", "is_company": True, "country_id": ref("base.ca").id}
)
contact = cenv["res.partner"].create(
    {"name": "OU20 BANK contact", "parent_id": parent.id, "type": "other"}
)
vendor, payee, nobody, mixed = cenv["res.partner"].create(
    [
        {"name": "OU20 BANK vendor"},
        {"name": "OU20 BANK payee"},
        {"name": "OU20 BANK nobody"},
        {"name": "OU20 BANK mixed"},
    ]
)
accounts = cenv["res.partner.bank"].create(
    [
        {"partner_id": contact.id, "acc_number": "OU20-BANK-1"},
        {"partner_id": vendor.id, "acc_number": "OU20-BANK-2"},
        {"partner_id": payee.id, "acc_number": "OU20-BANK-3"},
        {"partner_id": nobody.id, "acc_number": "OU20-BANK-4"},
        {"partner_id": mixed.id, "acc_number": "OU20-BANK-5"},
    ]
)
for company, partner, account in (
    (company_ca, vendor, accounts[1]),
    (company_ca, mixed, accounts[4]),
    (company_ca, mixed, accounts[4]),
    (company_jp, mixed, accounts[4]),
):
    move = (
        cenv["account.move"]
        .with_company(company)
        .create(
            {
                "move_type": "in_invoice",
                "partner_id": partner.id,
                "invoice_date": "2026-01-15",
            }
        )
    )
    move.partner_bank_id = account
journal = cenv["account.journal"].search(
    [("company_id", "=", company_jp.id), ("type", "=", "bank")], limit=1
)
payment = (
    cenv["account.payment"]
    .with_company(company_jp)
    .create(
        {
            "payment_type": "outbound",
            "partner_type": "supplier",
            "partner_id": payee.id,
            "amount": 100,
            "journal_id": journal.id,
        }
    )
)
payment.partner_bank_id = accounts[2]
env.flush_all()
env.cr.execute(
    "UPDATE res_partner SET country_id = NULL WHERE id IN %s",
    (tuple((contact | vendor | payee | nobody | mixed).ids),),
)
env.cr.commit()

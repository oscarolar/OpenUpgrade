env = locals().get("env")
ref = env.ref
companies = env["res.company"]
for name in ("OU20 VN A", "OU20 VN B"):
    company = env["res.company"].search([("name", "=", name)])
    if not company:
        company = env["res.company"].create(
            {
                "name": name,
                "country_id": ref("base.vn").id,
                "currency_id": ref("base.VND").id,
            }
        )
        env["account.chart.template"].try_loading("vn", company, install_demo=False)
    companies |= company
template = env["l10n_vn_edi_viettel.sinvoice.template"].create(
    {"name": "1/OU20", "template_invoice_type": "1"}
)
symbol = env["l10n_vn_edi_viettel.sinvoice.symbol"].create(
    {"name": "K26TOU", "invoice_template_id": template.id}
)
for company in companies:
    env["ir.default"].set(
        "res.partner", "l10n_vn_edi_symbol", symbol.id, company_id=company.id
    )
    if "l10n_vn_pos_default_symbol" in company._fields:
        company.l10n_vn_pos_default_symbol = symbol
    cenv = env(context=dict(env.context, allowed_company_ids=company.ids))
    partner = cenv["res.partner"].create(
        {
            "name": f"OU20 SInvoice customer {company.name}",
            "country_id": ref("base.vn").id,
        }
    )
    move = cenv["account.move"].create(
        {
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "ref": f"OU20 SInvoice {company.name}",
            "invoice_date": "2026-01-15",
            "l10n_vn_edi_invoice_symbol": symbol.id,
            "invoice_line_ids": [
                (
                    0,
                    0,
                    {
                        "name": "OU20",
                        "quantity": 1,
                        "price_unit": 100,
                        "tax_ids": [(5,)],
                    },
                )
            ],
        }
    )
    move.action_post()
    move.l10n_vn_edi_invoice_symbol = symbol
env.cr.commit()

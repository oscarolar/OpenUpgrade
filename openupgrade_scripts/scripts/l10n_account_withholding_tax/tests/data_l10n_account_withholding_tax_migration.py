env = locals().get("env")
company = env.ref("base.main_company")
withholding, regular = env["account.tax"].create(
    [
        {
            "name": "OU20 WHT on payment",
            "amount": -10,
            "type_tax_use": "sale",
            "is_withholding_tax_on_payment": True,
            "company_id": company.id,
        },
        {
            "name": "OU20 WHT regular",
            "amount": 10,
            "type_tax_use": "sale",
            "company_id": company.id,
        },
    ]
)
partner = env["res.partner"].create({"name": "OU20 WHT partner"})
journal = env["account.journal"].search(
    [("company_id", "=", company.id), ("type", "=", "bank")], limit=1
)
payments = env["account.payment"].create(
    [
        {
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": partner.id,
            "journal_id": journal.id,
            "amount": 100,
            "memo": memo,
        }
        for memo in ("OU20 WHT withheld", "OU20 WHT not withheld")
    ]
)
env.flush_all()
env.cr.execute(
    "UPDATE account_payment SET should_withhold_tax = (memo = 'OU20 WHT withheld') "
    "WHERE id IN %s",
    [tuple(payments.ids)],
)
env.cr.commit()

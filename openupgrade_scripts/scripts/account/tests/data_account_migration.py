env = locals().get("env")

company = env.company
partner = company.partner_id

env["account.group"].create(
    {"name": "OU group 1", "code_prefix_start": "1", "code_prefix_end": "1"}
)
env["account.group"].create(
    {"name": "OU group 10", "code_prefix_start": "10", "code_prefix_end": "10"}
)

ledger_a = env["account.journal.group"].create({"name": "OU ledger A"})
ledger_b = env["account.journal.group"].create({"name": "OU ledger B"})
journal_a = env["account.journal"].create(
    {"name": "OU journal A", "code": "OUA", "type": "general"}
)
env["account.journal"].create(
    {"name": "OU journal common", "code": "OUC", "type": "general"}
)
ledger_b.excluded_journal_ids = journal_a

payments = env["account.payment"].create(
    [
        {
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": partner.id,
            "amount": 10,
            "memo": f"OU payment {state}",
        }
        for state in ("in_process", "paid")
    ]
)
env.flush_all()
for payment in payments:
    env.cr.execute(
        "UPDATE account_payment SET state = %s WHERE id = %s",
        (payment.memo.replace("OU payment ", ""), payment.id),
    )

bill = env["account.move"].create(
    {
        "move_type": "in_invoice",
        "partner_id": partner.id,
        "ref": "OU deductible bill",
        "invoice_line_ids": [
            (
                0,
                0,
                {
                    "name": "OU half deductible",
                    "quantity": 1,
                    "price_unit": 100,
                    "deductible_amount": 50,
                },
            ),
            (
                0,
                0,
                {"name": "OU fully deductible", "quantity": 1, "price_unit": 100},
            ),
        ],
    }
)
entry = env["account.move"].create({"move_type": "entry", "ref": "OU entry to review"})
env.flush_all()
env.cr.execute(
    "UPDATE account_move SET state = 'posted', checked = FALSE WHERE id = %s",
    (entry.id,),
)

env.cr.commit()

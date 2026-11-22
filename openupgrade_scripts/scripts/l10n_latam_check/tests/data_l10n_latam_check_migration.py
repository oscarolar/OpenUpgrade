env = locals().get("env")
ref = env.ref
company = env["res.company"].search([("name", "=", "OU20 AR CHK")])
if not company:
    company = env["res.company"].create(
        {
            "name": "OU20 AR CHK",
            "country_id": ref("base.ar").id,
            "currency_id": ref("base.ARS").id,
        }
    )
    env["account.chart.template"].try_loading("ar_ri", company, install_demo=False)
branch = env["res.company"].create(
    {"name": "OU20 AR CHK branch", "parent_id": company.id}
)
env.user.company_ids |= company | branch
cenv = env(context=dict(env.context, allowed_company_ids=(company | branch).ids))
bank_one, bank_two = cenv["res.bank"].create(
    [{"name": "OU20 Banco Uno"}, {"name": "OU20 Banco Dos"}]
)
with_account, without_account = cenv["res.partner"].create(
    [{"name": "OU20 CHK with account"}, {"name": "OU20 CHK without account"}]
)
cenv["res.partner.bank"].create(
    [
        {
            "partner_id": with_account.id,
            "acc_number": "OU20-CHK-DOS",
            "bank_id": bank_two.id,
            "sequence": 1,
        },
        {
            "partner_id": with_account.id,
            "acc_number": "OU20-CHK-UNO",
            "bank_id": bank_one.id,
            "sequence": 2,
        },
        {
            "partner_id": without_account.id,
            "acc_number": "OU20-CHK-OTRO",
            "bank_id": bank_two.id,
        },
    ]
)
journal = cenv["account.journal"].search(
    [
        ("company_id", "=", company.id),
        ("inbound_payment_method_line_ids.code", "=", "new_third_party_checks"),
    ],
    limit=1,
)
method_line = journal.inbound_payment_method_line_ids.filtered(
    lambda line: line.code == "new_third_party_checks"
)
payments = cenv["account.payment"]
for partner, number in ((with_account, "00000001"), (without_account, "00000002")):
    payment = cenv["account.payment"].create(
        {
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": partner.id,
            "journal_id": journal.id,
            "payment_method_line_id": method_line.id,
            "date": "2026-01-10",
            "memo": f"OU20 CHK {number}",
            "l10n_latam_new_check_ids": [
                (
                    0,
                    0,
                    {
                        "name": number,
                        "payment_date": "2026-02-10",
                        "amount": 100,
                    },
                )
            ],
        }
    )
    payment.l10n_latam_new_check_ids.bank_id = bank_one
    payments |= payment
branch_journal = cenv["account.journal"].create(
    {
        "name": "OU20 CHK branch",
        "type": "cash",
        "code": "OU20B",
        "company_id": branch.id,
    }
)
operation = (
    cenv["account.payment"]
    .with_company(branch)
    .create(
        {
            "payment_type": "outbound",
            "partner_type": "supplier",
            "partner_id": with_account.id,
            "journal_id": branch_journal.id,
            "date": "2026-01-20",
            "amount": 100,
            "memo": "OU20 CHK transfer",
        }
    )
)
env.flush_all()
env.cr.execute(
    "UPDATE account_payment SET state = 'in_process' WHERE id IN %s",
    [tuple((payments | operation).ids)],
)
env.cr.execute(
    "INSERT INTO l10n_latam_check_account_payment_rel (check_id, payment_id) "
    "VALUES (%s, %s)",
    [payments[0].l10n_latam_new_check_ids.id, operation.id],
)
env.cr.commit()

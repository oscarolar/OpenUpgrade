env = locals().get("env")
ref = env.ref
type(env["account.edi.format"])._get_move_applicability = lambda self, move: None
company = env["res.company"].search([("name", "=", "OU20 SA ZATCA")])
if not company:
    company = env["res.company"].create(
        {
            "name": "OU20 SA ZATCA",
            "country_id": ref("base.sa").id,
            "currency_id": ref("base.SAR").id,
            "state_id": ref("base.state_sa_70").id,
        }
    )
    env["account.chart.template"].try_loading("sa", company, install_demo=False)
cenv = env(context=dict(env.context, allowed_company_ids=company.ids))
partner = cenv["res.partner"].create(
    {"name": "OU20 ZATCA customer", "country_id": ref("base.sa").id}
)
journal = cenv["account.journal"].search(
    [("company_id", "=", company.id), ("type", "=", "sale")], limit=1
)
zatca = ref("l10n_sa_edi.edi_sa_zatca")
cases = [
    ("OU20 ZATCA accepted", "sent", False, False, 1),
    ("OU20 ZATCA warning", "sent", "warning", "<p>Accepted with warnings</p>", 2),
    (
        "OU20 ZATCA timeout",
        "to_send",
        "warning",
        "<p>Unable to retrieve a response</p>",
        3,
    ),
    (
        "OU20 ZATCA rejected",
        "to_send",
        "error",
        "<p>Invoice rejected by ZATCA</p>",
        False,
    ),
    ("OU20 ZATCA to send", "to_send", False, False, False),
]
for ref_name, state, level, error, chain_index in cases:
    move = cenv["account.move"].create(
        {
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "journal_id": journal.id,
            "ref": ref_name,
            "invoice_date": "2026-01-15",
            "invoice_line_ids": [
                (
                    0,
                    0,
                    {
                        "name": ref_name,
                        "quantity": 1,
                        "price_unit": 100,
                        "tax_ids": [(5,)],
                    },
                )
            ],
        }
    )
    move.action_post()
    attachment = False
    if state == "sent":
        attachment = cenv["ir.attachment"].create(
            {
                "name": f"{ref_name}.xml",
                "raw": f"<Invoice><ID>{ref_name}</ID></Invoice>".encode(),
                "res_model": "account.move",
                "res_id": move.id,
                "mimetype": "application/xml",
            }
        )
    cenv["account.edi.document"].create(
        {
            "move_id": move.id,
            "edi_format_id": zatca.id,
            "state": state,
            "blocking_level": level,
            "error": error,
            "attachment_id": attachment and attachment.id,
        }
    )
    move.l10n_sa_chain_index = chain_index
sequence = journal._l10n_sa_edi_create_new_chain()
sequence.number_next = 4
journal.l10n_sa_chain_sequence_id = sequence
journal.l10n_sa_latest_submission_hash = "OU20HASH3"
env.cr.commit()

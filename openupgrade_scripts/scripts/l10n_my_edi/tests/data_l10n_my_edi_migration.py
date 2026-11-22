env = locals().get("env")
ref = env.ref
company = env["res.company"].search([("name", "=", "OU20 MY EDI")])
if not company:
    company = env["res.company"].create(
        {
            "name": "OU20 MY EDI",
            "country_id": ref("base.my").id,
            "currency_id": ref("base.MYR").id,
        }
    )
    env["account.chart.template"].try_loading("my", company, install_demo=False)
env.user.company_ids |= company
cenv = env(context=dict(env.context, allowed_company_ids=company.ids))
partner = cenv["res.partner"].create(
    {"name": "OU20 MyInvois customer", "country_id": ref("base.my").id}
)
sale = cenv["account.journal"].search(
    [("company_id", "=", company.id), ("type", "=", "sale")], limit=1
)
purchase = cenv["account.journal"].search(
    [("company_id", "=", company.id), ("type", "=", "purchase")], limit=1
)


def invoice(name, move_type, journal, **values):
    move = cenv["account.move"].create(
        {
            "move_type": move_type,
            "partner_id": partner.id,
            "journal_id": journal.id,
            "ref": name,
            "invoice_date": "2026-01-15",
            "invoice_line_ids": [
                (
                    0,
                    0,
                    {
                        "name": name,
                        "quantity": 1,
                        "price_unit": 100,
                        "tax_ids": [(5,)],
                    },
                )
            ],
            **values,
        }
    )
    move.action_post()
    return move


single = invoice("OU20 MY single", "out_invoice", sale)
first = invoice("OU20 MY consolidated 1", "out_invoice", sale)
second = invoice("OU20 MY consolidated 2", "out_invoice", sale)
refund = invoice("OU20 MY refund", "out_refund", sale)
debit = invoice("OU20 MY debit", "out_invoice", sale, debit_origin_id=single.id)
bill = invoice("OU20 MY bill", "in_invoice", purchase)
for move in single | refund | debit | bill:
    move._create_myinvois_document()
cenv["myinvois.document"].create(
    {
        "name": "OU20 MY CONSOLIDATED",
        "company_id": company.id,
        "currency_id": company.currency_id.id,
        "myinvois_issuance_date": "2026-01-31",
        "invoice_ids": [(6, 0, (second | first).ids)],
    }
)
config = cenv["pos.config"].create({"name": "OU20 MY PoS", "company_id": company.id})
config._action_to_open_ui()
product = cenv["product.product"].create({"name": "OU20 MY", "available_in_pos": True})
order = cenv["pos.order"].create(
    {
        "session_id": config.current_session_id.id,
        "partner_id": False,
        "amount_tax": 0,
        "amount_total": 100,
        "amount_paid": 100,
        "amount_return": 0,
        "lines": [
            (
                0,
                0,
                {
                    "product_id": product.id,
                    "qty": 1,
                    "price_unit": 100,
                    "price_subtotal": 100,
                    "price_subtotal_incl": 100,
                },
            )
        ],
    }
)
cenv["myinvois.document"].create(
    {
        "name": "OU20 MY POS",
        "company_id": company.id,
        "currency_id": company.currency_id.id,
        "myinvois_issuance_date": "2026-01-31",
        "pos_config_id": config.id,
        "pos_order_ids": [(6, 0, order.ids)],
    }
)
cenv["myinvois.document"].create(
    [
        {
            "name": "OU20 MY ORPHAN DRAFT",
            "company_id": company.id,
            "currency_id": company.currency_id.id,
            "myinvois_issuance_date": "2026-01-31",
        },
        {
            "name": "OU20 MY ORPHAN VALID",
            "company_id": company.id,
            "currency_id": company.currency_id.id,
            "myinvois_issuance_date": "2026-01-31",
            "myinvois_state": "valid",
            "myinvois_external_uuid": "OU20MYORPHANVALID",
        },
    ]
)
env.cr.commit()

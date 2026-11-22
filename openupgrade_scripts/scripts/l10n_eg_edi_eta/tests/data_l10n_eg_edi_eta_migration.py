import base64
import json

env = locals().get("env")
ref = env.ref
type(env["account.edi.format"])._get_move_applicability = lambda self, move: None
company = env["res.company"].search([("name", "=", "OU20 EG ETA")])
if not company:
    company = env["res.company"].create(
        {
            "name": "OU20 EG ETA",
            "country_id": ref("base.eg").id,
            "currency_id": ref("base.EGP").id,
        }
    )
    env["account.chart.template"].try_loading("eg", company, install_demo=False)
cenv = env(context=dict(env.context, allowed_company_ids=company.ids))
partner = cenv["res.partner"].create(
    {"name": "OU20 ETA customer", "country_id": ref("base.eg").id}
)
product = cenv["product.product"].create(
    {"name": "OU20 ETA product", "l10n_eg_eta_code": "EG-OU20-0001"}
)
eta = ref("l10n_eg_edi_eta.edi_eg_eta")
for ref_name, state, sent, level, error in (
    ("OU20 ETA sent", "sent", True, False, False),
    ("OU20 ETA cancelled", "cancelled", True, False, False),
    (
        "OU20 ETA invalid",
        "to_send",
        True,
        "error",
        "This invoice has been marked as invalid by the ETA.",
    ),
    ("OU20 ETA to send", "to_send", False, False, False),
):
    move = cenv["account.move"].create(
        {
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "ref": ref_name,
            "invoice_date": "2026-01-15",
            "invoice_line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "quantity": 1,
                        "price_unit": 100,
                        "tax_ids": [(5,)],
                    },
                )
            ],
        }
    )
    move.action_post()
    if sent:
        key = ref_name.split()[-1].upper()
        move.l10n_eg_eta_json_doc_file = base64.b64encode(
            json.dumps(
                {
                    "request": {"internalID": move.name},
                    "response": {
                        "l10n_eg_uuid": f"UUID-OU20-{key}",
                        "l10n_eg_long_id": f"LONG-OU20-{key}",
                        "l10n_eg_internal_id": move.name,
                        "l10n_eg_hash_key": f"HASH-OU20-{key}",
                        "l10n_eg_submission_number": f"SUB-OU20-{key}",
                    },
                }
            ).encode()
        )
    cenv["account.edi.document"].create(
        {
            "move_id": move.id,
            "edi_format_id": eta.id,
            "state": state,
            "blocking_level": level,
            "error": error,
        }
    )
env.cr.commit()

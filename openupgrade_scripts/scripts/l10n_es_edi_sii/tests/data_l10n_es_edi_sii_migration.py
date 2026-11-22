import json

env = locals().get("env")
ref = env.ref
type(env["account.edi.format"])._get_move_applicability = lambda self, move: None
company = env["res.company"].search([("name", "=", "OU20 ES SII")])
if not company:
    company = env["res.company"].create(
        {
            "name": "OU20 ES SII",
            "country_id": ref("base.es").id,
            "currency_id": ref("base.EUR").id,
        }
    )
    env["account.chart.template"].try_loading("es_pymes", company, install_demo=False)
cenv = env(context=dict(env.context, allowed_company_ids=company.ids))
partner = cenv["res.partner"].create(
    {"name": "OU20 SII customer", "country_id": ref("base.es").id}
)
sii = ref("l10n_es_edi_sii.edi_es_sii")
cases = [
    ("OU20 SII sent", "sent", False, False, "CSV-OU20-SENT"),
    (
        "OU20 SII warning",
        "sent",
        "warning",
        "<p>Aceptada con errores</p>",
        "CSV-OU20-WARN",
    ),
    ("OU20 SII to cancel", "to_cancel", False, False, "CSV-OU20-TOCANCEL"),
    ("OU20 SII cancelled", "cancelled", False, False, "CSV-OU20-CANCELLED"),
    ("OU20 SII error", "to_send", "error", "<p>Certificado no válido</p>", False),
]
for ref_name, state, level, error, csv in cases:
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
    if state != "to_send":
        attachment = cenv["ir.attachment"].create(
            {
                "name": f"{ref_name}.json",
                "raw": json.dumps({"ref": ref_name}).encode(),
                "res_model": "account.move",
                "res_id": move.id,
                "mimetype": "application/json",
            }
        )
    cenv["account.edi.document"].create(
        {
            "move_id": move.id,
            "edi_format_id": sii.id,
            "state": state,
            "blocking_level": level,
            "error": error,
            "attachment_id": attachment and attachment.id,
        }
    )
    if csv:
        move.l10n_es_edi_csv = csv
company.l10n_es_sii_tax_agency = "aeat"
env.cr.commit()

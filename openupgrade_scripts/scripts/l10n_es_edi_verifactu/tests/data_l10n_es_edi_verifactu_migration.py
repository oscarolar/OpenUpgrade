import json

env = locals().get("env")
ref = env.ref
type(env["account.edi.format"])._get_move_applicability = lambda self, move: None
company = env["res.company"].search([("name", "=", "OU20 ES VF")])
if not company:
    company = env["res.company"].create(
        {
            "name": "OU20 ES VF",
            "country_id": ref("base.es").id,
            "currency_id": ref("base.EUR").id,
        }
    )
    env["account.chart.template"].try_loading("es_pymes", company, install_demo=False)
company.l10n_es_edi_verifactu_special_vat_regime = "recargo"
cenv = env(context=dict(env.context, allowed_company_ids=company.ids))
partner = cenv["res.partner"].create(
    {"name": "OU20 VF customer", "country_id": ref("base.es").id}
)
sequence = company.sudo()._l10n_es_edi_verifactu_get_chain_sequence()
Document = cenv["l10n_es_edi_verifactu.document"].sudo()
for ref_name, move_type in (
    ("OU20 VF 1", "out_invoice"),
    ("OU20 VF 2", "out_invoice"),
    ("OU20 VF 3", "out_refund"),
):
    move = cenv["account.move"].create(
        {
            "move_type": move_type,
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
    if move_type == "out_refund":
        move.l10n_es_edi_verifactu_refund_reason = "R1"
    else:
        move.l10n_es_edi_verifactu_clave_regimen = "02"
    chain_index = int(sequence.next_by_id())
    document = Document.create(
        {
            "company_id": company.id,
            "move_id": move.id,
            "chain_index": chain_index,
            "document_type": "submission",
            "state": "accepted",
            "response_csv": f"VF-CSV-{chain_index}",
        }
    )
    document.json_attachment_id = (
        cenv["ir.attachment"]
        .sudo()
        .create(
            {
                "name": f"verifactu_registro_{chain_index}_alta.json",
                "raw": json.dumps(
                    {"RegistroAlta": {"Huella": f"OU20HUELLA{chain_index}"}}
                ).encode(),
                "res_model": Document._name,
                "res_id": document.id,
                "mimetype": "application/json",
            }
        )
    )
company.l10n_es_edi_verifactu_next_batch_time = "2026-01-15 10:00:00"
env.cr.commit()

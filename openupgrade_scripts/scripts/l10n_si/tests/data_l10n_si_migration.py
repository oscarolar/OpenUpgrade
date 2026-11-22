import json
import logging

env = locals().get("env")
ref = env.ref
COUNTRY = "si"
NAME = "OU20 TAGS SI"
company = env["res.company"].search([("name", "=", NAME)])
if not company:
    country = ref(f"base.{COUNTRY}")
    company = env["res.company"].create(
        {
            "name": NAME,
            "country_id": country.id,
            "currency_id": country.currency_id.id,
        }
    )
    env["account.chart.template"].try_loading("si", company, install_demo=False)
env.user.company_ids |= company
cenv = env(context=dict(env.context, allowed_company_ids=company.ids))
taxes = (
    cenv["account.tax"]
    .with_context(active_test=False)
    .search(
        [
            ("company_id", "=", company.id),
            ("type_tax_use", "in", ("sale", "purchase")),
            ("amount_type", "=", "percent"),
        ]
    )
    .filtered(lambda tax: tax.repartition_line_ids.tag_ids)
)
taxes.active = True
partner = cenv["res.partner"].create(
    {"name": f"{NAME} partner", "country_id": company.country_id.id}
)
journals = cenv["account.journal"].search([("company_id", "=", company.id)])
if "edi_format_ids" in journals._fields:
    journals.edi_format_ids = [(5, 0, 0)]
moves = cenv["account.move"]
for move_type, use in (
    ("out_invoice", "sale"),
    ("out_refund", "sale"),
    ("in_invoice", "purchase"),
    ("in_refund", "purchase"),
):
    for tax in taxes.filtered(lambda tax, use=use: tax.type_tax_use == use):
        try:
            with env.cr.savepoint():
                move = cenv["account.move"].create(
                    {
                        "move_type": move_type,
                        "partner_id": partner.id,
                        "invoice_date": "2026-01-15",
                        "invoice_line_ids": [
                            (
                                0,
                                0,
                                {
                                    "name": tax.name,
                                    "quantity": 1,
                                    "price_unit": 1000,
                                    "tax_ids": [(6, 0, tax.ids)],
                                },
                            )
                        ],
                    }
                )
                move.action_post()
                moves |= move
        except Exception as error:  # noqa: BLE001
            logging.getLogger(__name__).warning(
                "%s: %s %s: %s", NAME, tax.name, move_type, error
            )


def tag_names(tags):
    return sorted(tags.with_context(lang="en_US").mapped("name"))


snapshot = {
    "taxes": {
        tax.get_external_id()[tax.id]: [
            [
                line.document_type,
                line.repartition_type,
                tag_names(line.tag_ids),
                sorted(line.tag_ids.ids),
            ]
            for line in tax.repartition_line_ids.sorted(
                lambda line: (
                    line.document_type,
                    line.repartition_type,
                    line.sequence,
                    line.id,
                )
            )
        ]
        for tax in taxes
    },
    "move_lines": {
        str(line.id): tag_names(line.tax_tag_ids)
        for line in moves.line_ids
        if line.tax_tag_ids
    },
}
env["ir.config_parameter"].sudo().set_param(
    f"ou20.l10n_tax_tags.{COUNTRY}", json.dumps(snapshot)
)
env.cr.commit()

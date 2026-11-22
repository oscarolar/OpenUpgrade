env = locals().get("env")

env["res.partner.bank"].create(
    [
        {
            "acc_number": "OU0001234567",
            "partner_id": env.company.partner_id.id,
            "bank_id": env.ref("l10n_mx.acc_bank_002_BANAMEX").id,
            "l10n_mx_edi_clabe": "002010077777777771",
        },
        {
            "acc_number": "012180001234567895",
            "partner_id": env.company.partner_id.id,
            "bank_id": env.ref("l10n_mx.acc_bank_012_BBVA_BANCOMER").id,
            "l10n_mx_edi_clabe": "012180001234567895",
        },
        {
            "acc_number": "014180001111111117",
            "partner_id": env.company.partner_id.id,
            "bank_id": env.ref("l10n_mx.acc_bank_014_SANTANDER").id,
        },
        {
            "acc_number": "OU0007654321",
            "partner_id": env.company.partner_id.id,
            "bank_id": env.ref("l10n_mx.acc_bank_014_SANTANDER").id,
            "l10n_mx_edi_clabe": "014180001111111117",
        },
    ]
)

env.ref("base.MXN").active = True
mx_company = env["res.company"].create(
    {
        "name": "OU MX Company",
        "country_id": env.ref("base.mx").id,
        "currency_id": env.ref("base.MXN").id,
    }
)
env.user.company_ids |= mx_company
env["account.chart.template"].try_loading("mx", company=mx_company, install_demo=False)
mx_company.quick_edit_mode = "out_invoices"

env.cr.commit()

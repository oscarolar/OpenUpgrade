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
    ]
)

env.cr.commit()

env = locals().get("env")

env["res.partner"].create(
    {
        "name": "OU PE DNI partner",
        "country_id": env.ref("base.pe").id,
        "l10n_latam_identification_type_id": env.ref("l10n_pe.it_DNI").id,
        "vat": "40000004",
    }
)

env.cr.commit()

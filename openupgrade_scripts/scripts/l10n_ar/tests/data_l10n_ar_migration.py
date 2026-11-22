env = locals().get("env")

argentina = env.ref("base.ar")
env["res.partner"].create(
    [
        {
            "name": "OU AR DNI partner",
            "country_id": argentina.id,
            "l10n_latam_identification_type_id": env.ref("l10n_ar.it_dni").id,
            "vat": "26254396",
        },
        {
            "name": "OU AR CUIT partner",
            "is_company": True,
            "country_id": argentina.id,
            "l10n_latam_identification_type_id": env.ref("l10n_ar.it_cuit").id,
            "vat": "30714295698",
        },
        {
            "name": "OU AR CI partner",
            "country_id": argentina.id,
            "state_id": env.ref("base.state_ar_b").id,
            "l10n_latam_identification_type_id": env.ref("l10n_ar.it_CBA").id,
            "vat": "12345678",
        },
    ]
)

env.cr.commit()

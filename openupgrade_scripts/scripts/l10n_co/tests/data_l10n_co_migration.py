env = locals().get("env")

env["res.partner"].create(
    {
        "name": "OU CO CC partner",
        "country_id": env.ref("base.co").id,
        "l10n_latam_identification_type_id": env.ref(
            "l10n_co.national_citizen_id"
        ).id,
        "vat": "1020304050",
    }
)

env.cr.commit()

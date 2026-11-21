env = locals().get("env")
env["hr.work.entry.type"].create(
    {
        "name": "OpenUpgrade v20 blocking type",
        "code": "146.00",
        "country_id": env.ref("base.be").id,
    }
)
env.ref("hr_work_entry.l10n_be_work_entry_type_strike").name = "OpenUpgrade v20 strike"
env.ref("hr_work_entry.l10n_be_work_entry_type_extra_legal").code = "OU20XL"
env.ref("hr_work_entry.l10n_mx_work_entry_type_maternity_imss").amount_rate = 0.5
env.cr.commit()

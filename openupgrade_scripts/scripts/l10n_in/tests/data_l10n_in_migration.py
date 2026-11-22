import base64

env = locals().get("env")
ref = env.ref
for name, registered in (("OU20 IN GST", True), ("OU20 IN NOGST", False)):
    company = env["res.company"].search([("name", "=", name)])
    if not company:
        company = env["res.company"].create(
            {
                "name": name,
                "country_id": ref("base.in").id,
                "currency_id": ref("base.INR").id,
                "state_id": ref("base.state_in_gj").id,
            }
        )
        env["account.chart.template"].try_loading("in", company, install_demo=False)
    company.l10n_in_is_gst_registered = registered
pan = env["l10n_in.pan.entity"].create({"name": "AAAPL1234C"})
pan.write(
    {
        "tds_certificate": base64.b64encode(b"%PDF-1.4 OU20 TDS certificate"),
        "tds_certificate_filename": "ou20_tds_certificate.pdf",
    }
)
env["l10n_in.pan.entity"].create({"name": "BBBPL1234C"})
env.cr.commit()

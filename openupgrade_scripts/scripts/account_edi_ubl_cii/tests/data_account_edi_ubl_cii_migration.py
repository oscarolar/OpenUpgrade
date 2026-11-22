env = locals().get("env")

partner = env["res.partner"].create(
    {"name": "OU Peppol GLN partner", "country_id": env.ref("base.be").id}
)
env.flush_all()
env.cr.execute(
    """
    UPDATE res_partner
    SET peppol_eas = '0088', peppol_endpoint = '5401234567898'
    WHERE id = %s
    """,
    (partner.id,),
)

env.cr.commit()

env = locals().get("env")
ref = env.ref
Partner = env["res.partner"]


def ou20_partner(name, state_xmlid, **vals):
    state = ref(state_xmlid)
    return Partner.search([("name", "=", name)]) or Partner.create(
        {
            "name": name,
            "country_id": state.country_id.id,
            "state_id": state.id,
            **vals,
        }
    )


jeddah = ou20_partner("OU20 state Jeddah", "base.state_sa_40")
ou20_partner("OU20 state Jeddah Industrial City", "base.state_sa_41")
ou20_partner("OU20 state King Fhad", "base.state_sa_49")
ou20_partner("OU20 state Daman", "base.state_in_dd")
ou20_partner("OU20 state 6th of October", "base.state_eg_su")
ou20_partner(
    "OU20 state Riyadh delivery",
    "base.state_sa_70",
    parent_id=jeddah.id,
    type="delivery",
)
Bank = env["res.bank"]
Bank.search([("name", "=", "OU20 Riyadh Dry Port bank")]) or Bank.create(
    {
        "name": "OU20 Riyadh Dry Port bank",
        "country": ref("base.sa").id,
        "state": ref("base.state_sa_71").id,
    }
)
FiscalPosition = env["account.fiscal.position"]
FiscalPosition.search([("name", "=", "OU20 Mecca cities")]) or FiscalPosition.create(
    {
        "name": "OU20 Mecca cities",
        "country_id": ref("base.sa").id,
        "state_ids": [
            (
                6,
                0,
                [
                    ref("base.state_sa_40").id,
                    ref("base.state_sa_41").id,
                    ref("base.state_sa_54").id,
                ],
            )
        ],
    }
)
env["ir.default"].set(
    "res.partner",
    "state_id",
    ref("base.state_sa_40").id,
    user_id=ref("base.user_admin").id,
)
env.cr.commit()

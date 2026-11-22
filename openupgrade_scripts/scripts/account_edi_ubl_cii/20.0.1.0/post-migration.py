# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _res_partner_routing(env):
    """
    res.partner#routing_scheme and routing_endpoint replace peppol_eas and
    peppol_endpoint. Their compute reads the identifiers of the partner, which
    do not hold the Peppol endpoints yet, so keep the address the partner was
    set to receive its documents on.
    """
    if not openupgrade.column_exists(env.cr, "res_partner", "peppol_endpoint"):
        return
    schemes = [
        scheme
        for scheme, _label in env["res.partner"]._fields["routing_scheme"].selection
    ]
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_partner
        SET routing_scheme = peppol_eas, routing_endpoint = peppol_endpoint
        WHERE peppol_eas = ANY(%s)
            AND COALESCE(peppol_endpoint, '') <> ''
            AND (
                routing_scheme IS DISTINCT FROM peppol_eas
                OR routing_endpoint IS DISTINCT FROM peppol_endpoint
            )
        """,
        (schemes,),
    )
    env["res.partner"].invalidate_model(["routing_scheme", "routing_endpoint"])


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "account_edi_ubl_cii", "20.0.1.0/noupdate_changes.xml")
    _res_partner_routing(env)

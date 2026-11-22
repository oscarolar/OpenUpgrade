# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _res_partner_peppol_endpoint(env):
    """
    res.partner#peppol_eas and peppol_endpoint are gone: the endpoint is the
    additional identifier whose scheme is the EAS code. Endpoints that are the
    tax id of the partner already live in vat.
    """
    if not openupgrade.column_exists(env.cr, "res_partner", "peppol_endpoint"):
        return
    ResPartner = env["res.partner"]
    additional = ResPartner._get_all_additional_identifiers_metadata()
    for scheme, metadata in ResPartner._get_all_identifiers_metadata_by_scheme().items():
        if metadata["key"] not in additional:
            continue
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE res_partner
            SET additional_identifiers =
                jsonb_build_object(%s, peppol_endpoint)
                || COALESCE(additional_identifiers, '{}'::jsonb)
            WHERE peppol_eas = %s AND COALESCE(peppol_endpoint, '') <> ''
            """,
            (metadata["key"], scheme),
        )


def _res_partner_routing(env):
    """
    res.partner#routing_scheme and routing_endpoint replace peppol_eas and
    peppol_endpoint. They were computed when the module was loaded, before the
    endpoints were moved, so keep the address the partner was set to receive
    its documents on.
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
    _res_partner_peppol_endpoint(env)
    _res_partner_routing(env)

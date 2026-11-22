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


@openupgrade.migrate()
def migrate(env, version):
    _res_partner_peppol_endpoint(env)

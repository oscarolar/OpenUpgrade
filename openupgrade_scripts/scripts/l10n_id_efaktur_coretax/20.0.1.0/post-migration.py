# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _res_partner_additional_identifiers(env):
    """
    res.partner#l10n_id_tku is now read from additional_identifiers
    """
    if not openupgrade.column_exists(env.cr, "res_partner", "l10n_id_tku"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_partner
        SET additional_identifiers =
            jsonb_build_object('ID_TKU', l10n_id_tku)
            || COALESCE(additional_identifiers, '{}'::jsonb)
        WHERE COALESCE(l10n_id_tku, '') <> ''
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _res_partner_additional_identifiers(env)

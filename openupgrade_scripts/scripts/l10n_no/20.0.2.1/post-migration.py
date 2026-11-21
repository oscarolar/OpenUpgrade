# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _res_partner_additional_identifiers(env):
    """
    res.partner#l10n_no_bronnoysund_number is now read from additional_identifiers
    """
    if not openupgrade.column_exists(env.cr, "res_partner", "l10n_no_bronnoysund_number"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_partner
        SET additional_identifiers =
            jsonb_build_object('NO_EN', l10n_no_bronnoysund_number)
            || COALESCE(additional_identifiers, '{}'::jsonb)
        WHERE COALESCE(l10n_no_bronnoysund_number, '') <> ''
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _res_partner_additional_identifiers(env)

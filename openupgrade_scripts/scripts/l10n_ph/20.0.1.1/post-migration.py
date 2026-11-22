# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _res_company_l10n_ph_rdo(env):
    """
    res.company#l10n_ph_rdo is now stored on the company instead of being
    related to its partner, where the 19.0 value lives
    """
    if not openupgrade.column_exists(env.cr, "res_partner", "l10n_ph_rdo"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_company rc
        SET l10n_ph_rdo = rp.l10n_ph_rdo
        FROM res_partner rp
        WHERE rp.id = rc.partner_id
            AND COALESCE(rp.l10n_ph_rdo, '') <> ''
            AND COALESCE(rc.l10n_ph_rdo, '') = ''
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _res_company_l10n_ph_rdo(env)

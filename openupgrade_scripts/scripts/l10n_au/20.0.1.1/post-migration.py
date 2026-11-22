# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _res_partner_bank_clearing_number(env):
    """
    res.partner.bank#aba_bsb is gone: the BSB is now the clearing number of the
    account, validated as such for Australia
    """
    if not openupgrade.column_exists(env.cr, "res_partner_bank", "aba_bsb"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_partner_bank
        SET clearing_number = aba_bsb
        WHERE COALESCE(aba_bsb, '') <> ''
            AND COALESCE(clearing_number, '') = ''
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _res_partner_bank_clearing_number(env)

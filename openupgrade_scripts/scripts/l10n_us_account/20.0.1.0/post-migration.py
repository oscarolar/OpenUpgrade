# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _res_partner_bank_intermediary_bank_bic(env):
    """
    res.bank#intermediary_bank_id (res.bank is merged into res.partner.bank)
    becomes res.partner.bank#intermediary_bank_bic: the BIC of the
    intermediary bank of the bank of the account
    """
    if not openupgrade.column_exists(env.cr, "res_bank", "intermediary_bank_id"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_partner_bank rpb
        SET intermediary_bank_bic = intermediary.bic
        FROM res_bank rb
        JOIN res_bank intermediary ON intermediary.id = rb.intermediary_bank_id
        WHERE rpb.bank_id = rb.id
            AND COALESCE(intermediary.bic, '') <> ''
            AND COALESCE(rpb.intermediary_bank_bic, '') = ''
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _res_partner_bank_intermediary_bank_bic(env)

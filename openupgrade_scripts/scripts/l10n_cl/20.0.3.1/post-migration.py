# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _res_partner_bank_clearing_number(env):
    """
    res.bank is merged into res.partner.bank and its code
    (res.bank#l10n_cl_sbif_code) is now the clearing number of the account.
    """
    if not openupgrade.column_exists(env.cr, "res_bank", "l10n_cl_sbif_code"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_partner_bank rpb
        SET clearing_number = rb.l10n_cl_sbif_code,
            clearing_label_id = COALESCE(
                (
                    SELECT res_id FROM ir_model_data
                    WHERE module = 'base' AND name = 'clearing_label_cl'
                ),
                rpb.clearing_label_id
            )
        FROM res_bank rb
        WHERE rpb.bank_id = rb.id
            AND COALESCE(rb.l10n_cl_sbif_code, '') <> ''
            AND COALESCE(rpb.clearing_number, '') = ''
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _res_partner_bank_clearing_number(env)

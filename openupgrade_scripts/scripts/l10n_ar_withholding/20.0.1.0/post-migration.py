# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _res_company_withholding_tax_base_account(env):
    """
    res.company#l10n_ar_tax_base_account_id is replaced by the generic
    withholding_tax_base_account_id of l10n_account_withholding_tax.
    """
    if not openupgrade.column_exists(
        env.cr, "res_company", "l10n_ar_tax_base_account_id"
    ):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_company
        SET withholding_tax_base_account_id = l10n_ar_tax_base_account_id
        WHERE l10n_ar_tax_base_account_id IS NOT NULL
            AND withholding_tax_base_account_id IS NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "l10n_ar_withholding", "20.0.1.0/noupdate_changes.xml")
    _res_company_withholding_tax_base_account(env)

# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _l10n_latam_check_bank_account_id(env):
    """
    l10n_latam.check#bank_id (res.bank, merged into res.partner.bank) becomes
    bank_account_id: use the account of the check partner at the bank of the
    check, never an account at another bank
    """
    if not openupgrade.column_exists(env.cr, "l10n_latam_check", "bank_id"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE l10n_latam_check chk
        SET bank_account_id = (
            SELECT rpb.id
            FROM res_partner_bank rpb
            WHERE rpb.partner_id = ap.partner_id
                AND rpb.bank_id = chk.bank_id
            ORDER BY rpb.active DESC, rpb.sequence, rpb.id
            LIMIT 1
        )
        FROM account_payment ap
        WHERE ap.id = chk.payment_id
            AND chk.bank_id IS NOT NULL
        """,
    )


def _l10n_latam_check_company_id(env):
    """
    l10n_latam.check#company_id is now the company holding the check, after
    the transfers between branches
    """
    checks = env["l10n_latam.check"].search([("operation_ids", "!=", False)])
    checks._compute_company_id()
    checks.flush_recordset(["company_id"])


@openupgrade.migrate()
def migrate(env, version):
    _l10n_latam_check_bank_account_id(env)
    _l10n_latam_check_company_id(env)

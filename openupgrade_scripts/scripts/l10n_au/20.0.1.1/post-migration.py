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


def _account_report_expression_obsolete(env):
    """
    The Australian tax report and the master BAS are removed, the BAS reports
    keep using their tax tags with signed formulas ('-G1'). The ORM removal of
    the obsolete expressions only looks for unsigned formulas: it would strip
    G1, G2, 1C, W2... from the taxes and archive or delete them. Remove the
    obsolete expressions by SQL so the tags stay on the taxes
    """
    openupgrade.logged_query(
        env.cr,
        """
        WITH obsolete AS (
            DELETE FROM ir_model_data imd
            WHERE imd.module = 'l10n_au'
                AND imd.model = 'account.report.expression'
                AND (imd.name LIKE %s OR imd.name LIKE %s)
            RETURNING imd.res_id
        )
        DELETE FROM account_report_expression expr
        USING obsolete
        WHERE expr.id = obsolete.res_id
        """,
        ("account\\_tax\\_report\\_%", "l10n\\_au\\_master\\_bas\\_%"),
    )


@openupgrade.migrate()
def migrate(env, version):
    _res_partner_bank_clearing_number(env)
    _account_report_expression_obsolete(env)

# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _res_partner_bank_clearing_number(env):
    """
    res.bank is merged into res.partner.bank and its ABM code
    (res.bank#l10n_mx_edi_code) is now the clearing number of the account,
    labelled 'ABM Code' for Mexico.
    """
    if not openupgrade.column_exists(env.cr, "res_bank", "l10n_mx_edi_code"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_partner_bank rpb
        SET clearing_number = rb.l10n_mx_edi_code,
            clearing_label_id = COALESCE(
                (
                    SELECT res_id FROM ir_model_data
                    WHERE module = 'base' AND name = 'clearing_label_mx'
                ),
                rpb.clearing_label_id
            )
        FROM res_bank rb
        WHERE rpb.bank_id = rb.id
            AND COALESCE(rb.l10n_mx_edi_code, '') <> ''
            AND COALESCE(rpb.clearing_number, '') = ''
        """,
    )


def _res_partner_bank_clabe(env):
    """
    res.partner.bank#l10n_mx_edi_clabe is gone: the CLABE is now the account
    number itself. When the account had a different number, keep the CLABE in
    the notes of the account so that it is not lost.
    """
    if not openupgrade.column_exists(env.cr, "res_partner_bank", "l10n_mx_edi_clabe"):
        return
    openupgrade.logged_query(
        env.cr,
        r"""
        UPDATE res_partner_bank
        SET note = concat_ws(
            E'\n', NULLIF(note, ''), 'CLABE: ' || l10n_mx_edi_clabe
        )
        WHERE COALESCE(l10n_mx_edi_clabe, '') <> ''
            AND regexp_replace(l10n_mx_edi_clabe, '\W', '', 'g')
                <> COALESCE(sanitized_account_number, '')
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _res_partner_bank_clearing_number(env)
    _res_partner_bank_clabe(env)

# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _res_company_l10n_vn_edi_symbol_id(env):
    """
    The default symbol of 19.0 was the company default of the company
    dependent res.partner#l10n_vn_edi_symbol; it is now
    res.company#l10n_vn_edi_symbol_id. A default shared by all companies
    points to the original symbol: each company takes its own copy
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_company rc
        SET l10n_vn_edi_symbol_id = defaults.symbol_id
        FROM (
            SELECT DISTINCT ON (rc2.id) rc2.id AS company_id, symbol.id AS symbol_id
            FROM res_company rc2
            JOIN ir_default idf
                ON idf.company_id = rc2.id OR idf.company_id IS NULL
            JOIN ir_model_fields imf ON imf.id = idf.field_id
            JOIN l10n_vn_edi_viettel_sinvoice_symbol origin
                ON origin.id::text = idf.json_value
            JOIN l10n_vn_edi_viettel_sinvoice_symbol symbol
                ON symbol.name = origin.name
                AND symbol.invoice_template_code = origin.invoice_template_code
                AND symbol.company_id = rc2.id
            WHERE imf.model = 'res.partner'
                AND imf.name = 'l10n_vn_edi_symbol'
                AND idf.user_id IS NULL
                AND idf.condition IS NULL
            ORDER BY rc2.id, idf.company_id NULLS LAST, symbol.id = origin.id DESC
        ) defaults
        WHERE defaults.company_id = rc.id
            AND rc.l10n_vn_edi_symbol_id IS NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _res_company_l10n_vn_edi_symbol_id(env)

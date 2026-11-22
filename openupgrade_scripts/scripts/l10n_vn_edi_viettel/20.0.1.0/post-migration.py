# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _sinvoice_symbol_template_code(env):
    """
    l10n_vn_edi_viettel.sinvoice.template is gone: its code is now stored on
    the symbol
    """
    if not openupgrade.column_exists(
        env.cr, "l10n_vn_edi_viettel_sinvoice_symbol", "invoice_template_id"
    ):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE l10n_vn_edi_viettel_sinvoice_symbol symbol
        SET invoice_template_code = template.name
        FROM l10n_vn_edi_viettel_sinvoice_template template
        WHERE template.id = symbol.invoice_template_id
            AND symbol.invoice_template_code IS NULL
        """,
    )


def _sinvoice_symbol_company_id(env):
    """
    Symbols now belong to one company: give each symbol the first company that
    used it and copy it for every other company whose invoices used it
    """
    cr = env.cr
    cr.execute(
        """
        SELECT DISTINCT l10n_vn_edi_invoice_symbol, company_id
        FROM account_move
        WHERE l10n_vn_edi_invoice_symbol IS NOT NULL
        ORDER BY 1, 2
        """
    )
    companies_by_symbol = {}
    for symbol_id, company_id in cr.fetchall():
        companies_by_symbol.setdefault(symbol_id, []).append(company_id)
    cr.execute(
        """
        SELECT rc.id
        FROM res_company rc
        LEFT JOIN res_country country ON country.id = rc.account_fiscal_country_id
        ORDER BY country.code = 'VN' DESC NULLS LAST, rc.id
        LIMIT 1
        """
    )
    default_company_id = cr.fetchone()[0]
    extra_columns = (
        "invoice_template_id,"
        if openupgrade.column_exists(
            cr, "l10n_vn_edi_viettel_sinvoice_symbol", "invoice_template_id"
        )
        else ""
    )
    cr.execute(
        """
        SELECT id FROM l10n_vn_edi_viettel_sinvoice_symbol
        WHERE company_id IS NULL
        """
    )
    for (symbol_id,) in cr.fetchall():
        company_ids = companies_by_symbol.get(symbol_id) or [default_company_id]
        cr.execute(
            """
            UPDATE l10n_vn_edi_viettel_sinvoice_symbol
            SET company_id = %s
            WHERE id = %s
            """,
            (company_ids[0], symbol_id),
        )
        for company_id in company_ids[1:]:
            cr.execute(
                f"""
                INSERT INTO l10n_vn_edi_viettel_sinvoice_symbol (
                    name, invoice_template_code, company_id, active,
                    {extra_columns}
                    create_uid, create_date, write_uid, write_date
                )
                SELECT
                    name, invoice_template_code, %(company_id)s, active,
                    {extra_columns}
                    create_uid, create_date, write_uid, write_date
                FROM l10n_vn_edi_viettel_sinvoice_symbol
                WHERE id = %(symbol_id)s
                RETURNING id
                """,
                {"company_id": company_id, "symbol_id": symbol_id},
            )
            new_symbol_id = cr.fetchone()[0]
            openupgrade.logged_query(
                cr,
                """
                UPDATE account_move
                SET l10n_vn_edi_invoice_symbol = %(new)s
                WHERE l10n_vn_edi_invoice_symbol = %(old)s
                    AND company_id = %(company_id)s
                """,
                {"new": new_symbol_id, "old": symbol_id, "company_id": company_id},
            )


def _res_company_l10n_vn_edi_symbol_id(env):
    """
    The default symbol of 19.0 was the company default of the company
    dependent res.partner#l10n_vn_edi_symbol; it is now
    res.company#l10n_vn_edi_symbol_id
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
            JOIN l10n_vn_edi_viettel_sinvoice_symbol symbol
                ON symbol.id::text = idf.json_value
            WHERE imf.model = 'res.partner'
                AND imf.name = 'l10n_vn_edi_symbol'
                AND idf.user_id IS NULL
                AND idf.condition IS NULL
                AND symbol.company_id = rc2.id
            ORDER BY rc2.id, idf.company_id NULLS LAST
        ) defaults
        WHERE defaults.company_id = rc.id
            AND rc.l10n_vn_edi_symbol_id IS NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _sinvoice_symbol_template_code(env)
    _sinvoice_symbol_company_id(env)
    _res_company_l10n_vn_edi_symbol_id(env)

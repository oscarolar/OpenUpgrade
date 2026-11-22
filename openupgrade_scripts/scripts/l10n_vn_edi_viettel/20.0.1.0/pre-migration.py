# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade
from psycopg2 import sql


def _sinvoice_symbol_template_code(env):
    """
    l10n_vn_edi_viettel.sinvoice.template is gone: its code is now stored on
    the symbol
    """
    if not openupgrade.column_exists(
        env.cr, "l10n_vn_edi_viettel_sinvoice_symbol", "invoice_template_id"
    ):
        return
    if not openupgrade.column_exists(
        env.cr, "l10n_vn_edi_viettel_sinvoice_symbol", "invoice_template_code"
    ):
        openupgrade.logged_query(
            env.cr,
            """
            ALTER TABLE l10n_vn_edi_viettel_sinvoice_symbol
            ADD COLUMN invoice_template_code VARCHAR
            """,
        )
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


_symbol_references = [
    ("account_move", "l10n_vn_edi_invoice_symbol", "company_id"),
    ("pos_config", "l10n_vn_pos_symbol", "company_id"),
    ("res_company", "l10n_vn_pos_default_symbol", "id"),
]

_symbol_defaults_query = """
    SELECT idf.json_value::integer AS symbol_id, rc.id AS company_id
    FROM ir_default idf
    JOIN ir_model_fields imf ON imf.id = idf.field_id
    JOIN res_company rc ON rc.id = idf.company_id OR (
        idf.company_id IS NULL
        AND rc.account_fiscal_country_id = (
            SELECT id FROM res_country WHERE code = 'VN'
        )
    )
    WHERE imf.model = 'res.partner'
        AND imf.name = 'l10n_vn_edi_symbol'
        AND idf.user_id IS NULL
        AND idf.condition IS NULL
        AND idf.json_value ~ '^[0-9]+$'
"""


def _sinvoice_symbol_company_id(env):
    """
    Symbols now belong to one company: give each symbol the first company that
    used it (invoices, PoS, company defaults) and copy it for every other
    company that used it, whose records then point to the copy. Done in the pre:
    an empty required column with a default is filled by the ORM with the
    current company
    """
    cr = env.cr
    references = [
        (table, column, company_column)
        for table, column, company_column in _symbol_references
        if openupgrade.column_exists(cr, table, column)
    ]
    queries = [
        sql.SQL(
            "SELECT {column} AS symbol_id, {company_column} AS company_id "
            "FROM {table} WHERE {column} IS NOT NULL"
        ).format(
            table=sql.Identifier(table),
            column=sql.Identifier(column),
            company_column=sql.Identifier(company_column),
        )
        for table, column, company_column in references
    ]
    queries.append(sql.SQL(_symbol_defaults_query))
    cr.execute(
        sql.SQL(
            """
            SELECT DISTINCT used.symbol_id, used.company_id
            FROM ({queries}) used
            JOIN l10n_vn_edi_viettel_sinvoice_symbol symbol
                ON symbol.id = used.symbol_id
            WHERE symbol.company_id IS NULL
            ORDER BY 1, 2
            """
        ).format(queries=sql.SQL(" UNION ").join(queries))
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
                    name, invoice_template_code, company_id,
                    {extra_columns}
                    create_uid, create_date, write_uid, write_date
                )
                SELECT
                    name, invoice_template_code, %(company_id)s,
                    {extra_columns}
                    create_uid, create_date, write_uid, write_date
                FROM l10n_vn_edi_viettel_sinvoice_symbol
                WHERE id = %(symbol_id)s
                RETURNING id
                """,
                {"company_id": company_id, "symbol_id": symbol_id},
            )
            params = {
                "new": cr.fetchone()[0],
                "old": symbol_id,
                "company_id": company_id,
            }
            for table, column, company_column in references:
                openupgrade.logged_query(
                    cr,
                    f"""
                    UPDATE {table}
                    SET {column} = %(new)s
                    WHERE {column} = %(old)s
                        AND {company_column} = %(company_id)s
                    """,
                    params,
                )
            openupgrade.logged_query(
                cr,
                """
                UPDATE ir_default idf
                SET json_value = %(new)s::text
                FROM ir_model_fields imf
                WHERE imf.id = idf.field_id
                    AND imf.model = 'res.partner'
                    AND imf.name = 'l10n_vn_edi_symbol'
                    AND idf.company_id = %(company_id)s
                    AND idf.json_value = %(old)s::text
                """,
                params,
            )


@openupgrade.migrate()
def migrate(env, version):
    if not openupgrade.table_exists(env.cr, "l10n_vn_edi_viettel_sinvoice_symbol"):
        return
    if not openupgrade.column_exists(
        env.cr, "l10n_vn_edi_viettel_sinvoice_symbol", "company_id"
    ):
        openupgrade.logged_query(
            env.cr,
            """
            ALTER TABLE l10n_vn_edi_viettel_sinvoice_symbol
            ADD COLUMN company_id INTEGER
            """,
        )
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE l10n_vn_edi_viettel_sinvoice_symbol
        DROP CONSTRAINT IF EXISTS l10n_vn_edi_viettel_sinvoice_symbol_name_template_uniq
        """,
    )
    _sinvoice_symbol_template_code(env)
    _sinvoice_symbol_company_id(env)

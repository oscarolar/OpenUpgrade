# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    if openupgrade.table_exists(
        env.cr, "l10n_vn_edi_viettel_sinvoice_symbol"
    ) and not openupgrade.column_exists(
        env.cr, "l10n_vn_edi_viettel_sinvoice_symbol", "company_id"
    ):
        openupgrade.logged_query(
            env.cr,
            """
            ALTER TABLE l10n_vn_edi_viettel_sinvoice_symbol
            ADD COLUMN company_id INTEGER
            """,
        )

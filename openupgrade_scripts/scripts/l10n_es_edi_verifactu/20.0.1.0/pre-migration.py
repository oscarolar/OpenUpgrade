# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _l10n_es_edi_verifactu_document_obligado_partner_id(env):
    """
    l10n_es_edi_verifactu.document#obligado_partner_id is new and required: in
    19.0 the company always issued its own documents
    """
    if not openupgrade.column_exists(
        env.cr, "l10n_es_edi_verifactu_document", "obligado_partner_id"
    ):
        openupgrade.logged_query(
            env.cr,
            """
            ALTER TABLE l10n_es_edi_verifactu_document
            ADD COLUMN obligado_partner_id INTEGER
            """,
        )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE l10n_es_edi_verifactu_document doc
        SET obligado_partner_id = res_company.partner_id
        FROM res_company
        WHERE res_company.id = doc.company_id
            AND doc.obligado_partner_id IS NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _l10n_es_edi_verifactu_document_obligado_partner_id(env)

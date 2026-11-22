# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _myinvois_document_invoice_values(env):
    """
    myinvois.document#move_type and journal_id are new and required, they come
    from the first invoice of the document; documents with several invoices
    are consolidated invoices, and documents of debit notes are flagged when
    debit notes are in use
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE myinvois_document doc
        SET move_type = am.move_type,
            journal_id = am.journal_id
        FROM (
            SELECT DISTINCT ON (rel.document_id)
                rel.document_id, move.move_type, move.journal_id
            FROM myinvois_document_invoice_rel rel
            JOIN account_move move ON move.id = rel.invoice_id
            ORDER BY rel.document_id, move.id
        ) am
        WHERE am.document_id = doc.id
            AND (doc.move_type IS NULL OR doc.journal_id IS NULL)
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE myinvois_document doc
        SET is_consolidated_invoice = TRUE
        WHERE doc.is_consolidated_invoice IS NOT TRUE
            AND (
                SELECT COUNT(*) FROM myinvois_document_invoice_rel rel
                WHERE rel.document_id = doc.id
            ) > 1
        """,
    )
    if openupgrade.column_exists(env.cr, "account_move", "debit_origin_id"):
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE myinvois_document doc
            SET is_debit_note = TRUE
            WHERE doc.is_debit_note IS NOT TRUE
                AND doc.move_type IN ('out_invoice', 'in_invoice')
                AND EXISTS (
                    SELECT 1 FROM myinvois_document_invoice_rel rel
                    JOIN account_move move ON move.id = rel.invoice_id
                    WHERE rel.document_id = doc.id
                        AND move.debit_origin_id IS NOT NULL
                )
            """,
        )


def _myinvois_document_pos_values(env):
    """
    Documents of PoS orders (l10n_my_edi_pos) are consolidated invoices of the
    journal of their PoS configuration, sequenced as customer invoices
    """
    if not openupgrade.table_exists(
        env.cr, "myinvois_document_pos_order_rel"
    ) or not openupgrade.column_exists(env.cr, "myinvois_document", "pos_config_id"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE myinvois_document doc
        SET move_type = COALESCE(doc.move_type, 'out_invoice'),
            journal_id = COALESCE(doc.journal_id, pc.journal_id),
            is_consolidated_invoice = TRUE
        FROM pos_config pc
        WHERE pc.id = doc.pos_config_id
            AND EXISTS (
                SELECT 1 FROM myinvois_document_pos_order_rel rel
                WHERE rel.document_id = doc.id
            )
            AND (
                doc.move_type IS NULL
                OR doc.journal_id IS NULL
                OR doc.is_consolidated_invoice IS NOT TRUE
            )
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _myinvois_document_invoice_values(env)
    _myinvois_document_pos_values(env)

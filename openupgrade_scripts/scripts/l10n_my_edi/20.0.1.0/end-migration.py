# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)

_active_states = ("in_progress", "valid", "rejected")


def _myinvois_document_orphans(env):
    """
    Documents without invoices nor PoS orders have no move_type nor journal_id
    to take from them, and both are required now. The ones never registered on
    MyInvois cannot be submitted any more: delete them. Keep the others as
    customer invoices of the journal of their PoS configuration, or of the
    first sales journal of their company. Runs after l10n_my_edi_pos filled
    the documents of PoS orders
    """
    pos_rel = openupgrade.table_exists(env.cr, "myinvois_document_pos_order_rel")
    pos_config = pos_rel and openupgrade.column_exists(
        env.cr, "myinvois_document", "pos_config_id"
    )
    pos_filter = (
        """
            AND NOT EXISTS (
                SELECT 1 FROM myinvois_document_pos_order_rel rel
                WHERE rel.document_id = doc.id
            )
        """
        if pos_rel
        else ""
    )
    env.cr.execute(
        f"""
        SELECT doc.id,
            doc.myinvois_external_uuid IS NULL
                AND doc.myinvois_submission_uid IS NULL
                AND COALESCE(doc.myinvois_state, '') NOT IN %s
        FROM myinvois_document doc
        WHERE (doc.move_type IS NULL OR doc.journal_id IS NULL)
            AND NOT EXISTS (
                SELECT 1 FROM myinvois_document_invoice_rel rel
                WHERE rel.document_id = doc.id
            )
            {pos_filter}
        """,
        (_active_states,),
    )
    rows = env.cr.fetchall()
    leftovers = [doc_id for doc_id, leftover in rows if leftover]
    kept = [doc_id for doc_id, leftover in rows if not leftover]
    if leftovers:
        env["myinvois.document"].sudo().with_context(active_test=False).browse(
            leftovers
        ).unlink()
        _logger.warning(
            "myinvois.document: deleted %s documents without invoices nor PoS "
            "orders that were never registered on MyInvois: %s",
            len(leftovers),
            leftovers,
        )
    if kept:
        pos_journal = (
            "(SELECT journal_id FROM pos_config WHERE id = doc.pos_config_id),"
            if pos_config
            else ""
        )
        openupgrade.logged_query(
            env.cr,
            f"""
            UPDATE myinvois_document doc
            SET move_type = COALESCE(doc.move_type, 'out_invoice'),
                journal_id = COALESCE(
                    doc.journal_id,
                    {pos_journal}
                    (
                        SELECT journal.id FROM account_journal journal
                        WHERE journal.company_id = doc.company_id
                            AND journal.type = 'sale'
                        ORDER BY journal.sequence, journal.id
                        LIMIT 1
                    )
                )
            WHERE doc.id = ANY(%s)
            """,
            (kept,),
        )
        _logger.warning(
            "myinvois.document: %s documents registered on MyInvois have no "
            "invoices nor PoS orders, they are kept as customer invoices: %s",
            len(kept),
            kept,
        )
    env.invalidate_all()
    return leftovers, kept


@openupgrade.migrate()
def migrate(env, version):
    _myinvois_document_orphans(env)

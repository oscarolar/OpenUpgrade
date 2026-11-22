# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _myinvois_document_pos_values(env):
    """
    Documents of PoS orders are consolidated invoices of the journal of their
    PoS configuration, sequenced as customer invoices. It runs after
    point_of_sale, which makes pos.config#journal_id the invoice journal
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
    _myinvois_document_pos_values(env)

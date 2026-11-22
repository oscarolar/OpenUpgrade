# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _l10n_es_edi_sii_document(env):
    """
    SII no longer uses account_edi: create one l10n_es_edi_sii.document per
    19.0 EDI document of the SII format, with the CSV of the invoice, so that
    the invoices keep their state and are not sent again
    """
    if not openupgrade.table_exists(env.cr, "account_edi_document"):
        return
    csv = (
        "am.l10n_es_edi_csv"
        if openupgrade.column_exists(env.cr, "account_move", "l10n_es_edi_csv")
        else "NULL"
    )
    openupgrade.logged_query(
        env.cr,
        f"""
        INSERT INTO l10n_es_edi_sii_document (
            move_id, state, csv, attachment_id, response_message,
            create_uid, create_date, write_uid, write_date
        )
        SELECT
            aed.move_id,
            CASE
                WHEN aed.state = 'sent' AND aed.blocking_level = 'warning'
                    AND COALESCE(aed.error, '') <> ''
                THEN 'accepted_with_errors'
                WHEN aed.state = 'sent' THEN 'accepted'
                WHEN aed.state IN ('to_cancel', 'cancelled') THEN aed.state
                ELSE 'to_send'
            END,
            CASE WHEN aed.state IN ('sent', 'to_cancel', 'cancelled')
                THEN {csv} END,
            aed.attachment_id,
            aed.error,
            aed.create_uid, aed.create_date, aed.write_uid, aed.write_date
        FROM account_edi_document aed
        JOIN account_edi_format aef ON aef.id = aed.edi_format_id
        JOIN account_move am ON am.id = aed.move_id
        WHERE aef.code = 'es_sii'
            AND NOT EXISTS (
                SELECT 1 FROM l10n_es_edi_sii_document doc
                WHERE doc.move_id = aed.move_id
            )
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _l10n_es_edi_sii_document(env)

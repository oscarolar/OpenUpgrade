# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _l10n_sa_edi_document(env):
    """
    ZATCA no longer uses account_edi: create one l10n_sa_edi.document (with a
    log) per 19.0 EDI document of the ZATCA format, keeping its state, signed
    XML, errors and chain index, and link it to the invoice. The chain head and
    the latest submission hash of the journals stay as they are
    """
    if not openupgrade.table_exists(env.cr, "account_edi_document"):
        return
    chain_index = (
        "am.l10n_sa_chain_index"
        if openupgrade.column_exists(env.cr, "account_move", "l10n_sa_chain_index")
        else "NULL"
    )
    env.cr.execute(
        f"""
        INSERT INTO l10n_sa_edi_document (
            res_model, res_id, attachment_id, state, message,
            l10n_sa_chain_index, company_id, journal_id,
            create_uid, create_date, write_uid, write_date
        )
        SELECT
            'account.move', am.id, aed.attachment_id,
            CASE
                WHEN aed.state = 'sent' AND aed.blocking_level = 'warning'
                    AND COALESCE(aed.error, '') <> ''
                THEN 'warning'
                WHEN aed.state IN ('sent', 'to_cancel', 'cancelled')
                THEN 'accepted'
                WHEN COALESCE(aed.error, '') <> '' AND {chain_index} IS NOT NULL
                THEN 'unknown'
                WHEN COALESCE(aed.error, '') <> ''
                    AND aed.blocking_level = 'error'
                THEN 'rejected'
                ELSE 'to_send'
            END,
            CASE WHEN COALESCE(aed.error, '') <> ''
                THEN jsonb_build_object('en_US', aed.error) END,
            {chain_index}, am.company_id, am.journal_id,
            aed.create_uid, aed.create_date, aed.write_uid, aed.write_date
        FROM account_edi_document aed
        JOIN account_edi_format aef ON aef.id = aed.edi_format_id
        JOIN account_move am ON am.id = aed.move_id
        WHERE aef.code = 'sa_zatca'
            AND NOT EXISTS (
                SELECT 1 FROM l10n_sa_edi_document doc
                WHERE doc.res_model = 'account.move' AND doc.res_id = am.id
            )
        RETURNING id
        """
    )
    document_ids = [row[0] for row in env.cr.fetchall()]
    if not document_ids:
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_move am
        SET l10n_sa_edi_document_id = doc.id
        FROM l10n_sa_edi_document doc
        WHERE doc.id = ANY(%(ids)s)
            AND doc.res_model = 'account.move'
            AND doc.res_id = am.id
            AND am.l10n_sa_edi_document_id IS NULL
        """,
        {"ids": document_ids},
    )
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO l10n_sa_edi_log (
            l10n_sa_edi_document_id, state, attachment_name, is_test, message,
            create_uid, create_date, write_uid, write_date
        )
        SELECT
            doc.id, doc.state, att.name,
            COALESCE(rc.l10n_sa_api_mode, 'sandbox') <> 'prod',
            doc.message,
            doc.write_uid, doc.write_date, doc.write_uid, doc.write_date
        FROM l10n_sa_edi_document doc
        JOIN res_company rc ON rc.id = doc.company_id
        LEFT JOIN ir_attachment att ON att.id = doc.attachment_id
        WHERE doc.id = ANY(%(ids)s)
        """,
        {"ids": document_ids},
    )
    moves = env["account.move"].search(
        [("l10n_sa_edi_document_id", "in", document_ids)]
    )
    moves._compute_l10n_sa_is_test()
    moves.flush_recordset(["l10n_sa_is_test"])


def _account_tax_ubl_cii_tax_exemption_reason_code(env):
    """
    account.tax#l10n_sa_exemption_reason_code is replaced by the generic
    ubl_cii_tax_exemption_reason_code, which l10n_sa_edi extends with the same
    VATEX-SA codes
    """
    if not openupgrade.column_exists(
        env.cr, "account_tax", "l10n_sa_exemption_reason_code"
    ):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_tax
        SET ubl_cii_tax_exemption_reason_code = l10n_sa_exemption_reason_code
        WHERE COALESCE(l10n_sa_exemption_reason_code, '') <> ''
            AND ubl_cii_tax_exemption_reason_code IS NULL
        """,
    )


def _res_partner_additional_identifiers(env):
    """
    res.partner#l10n_sa_edi_additional_identification_scheme / _number are now
    read from additional_identifiers under the key 'SA_<scheme>'
    """
    if not openupgrade.column_exists(
        env.cr, "res_partner", "l10n_sa_edi_additional_identification_number"
    ):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_partner
        SET additional_identifiers =
            jsonb_build_object(
                'SA_' || l10n_sa_edi_additional_identification_scheme,
                l10n_sa_edi_additional_identification_number
            )
            || COALESCE(additional_identifiers, '{}'::jsonb)
        WHERE COALESCE(l10n_sa_edi_additional_identification_scheme, '') <> ''
            AND COALESCE(l10n_sa_edi_additional_identification_number, '') <> ''
            AND NOT EXISTS (
                SELECT 1 FROM jsonb_object_keys(
                    COALESCE(additional_identifiers, '{}'::jsonb)
                ) AS identifier(key)
                WHERE left(identifier.key, 3) = 'SA_'
            )
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _account_tax_ubl_cii_tax_exemption_reason_code(env)
    _res_partner_additional_identifiers(env)
    _l10n_sa_edi_document(env)

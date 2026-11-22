# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _product_product_l10n_eg_eta_code(env):
    """
    product.product#l10n_eg_eta_code is now company dependent: the 19.0 code
    applies to every company
    """
    legacy_column = openupgrade.get_legacy_name("l10n_eg_eta_code")
    if not openupgrade.column_exists(env.cr, "product_product", legacy_column):
        return
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE product_product
        SET l10n_eg_eta_code = (
            SELECT jsonb_object_agg(res_company.id, product_product.{legacy_column})
            FROM res_company
        )
        WHERE COALESCE({legacy_column}, '') <> ''
            AND l10n_eg_eta_code IS NULL
        """,
    )


def _res_company_l10n_eg_edi_api_mode(env):
    """
    res.company#l10n_eg_production_env becomes the l10n_eg_edi_api_mode selection
    """
    if not openupgrade.column_exists(env.cr, "res_company", "l10n_eg_production_env"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_company
        SET l10n_eg_edi_api_mode = CASE
            WHEN l10n_eg_production_env THEN 'production'
            ELSE 'preproduction'
        END
        WHERE l10n_eg_edi_api_mode IS NULL
            AND EXISTS (
                SELECT 1 FROM res_country
                WHERE res_country.id = res_company.account_fiscal_country_id
                    AND res_country.code = 'EG'
            )
        """,
    )


def _l10n_eg_invoicing_threshold(env):
    """
    The invoicing threshold of each company is now one system parameter: keep
    the strictest threshold of the Egyptian companies
    """
    if not openupgrade.column_exists(
        env.cr, "res_company", "l10n_eg_invoicing_threshold"
    ):
        return
    params = env["ir.config_parameter"].sudo()
    if params.get_str("l10n_eg_edi_eta.invoicing_threshold"):
        return
    env.cr.execute(
        """
        SELECT MIN(COALESCE(res_company.l10n_eg_invoicing_threshold, 0))
        FROM res_company
        JOIN res_country ON res_country.id = res_company.account_fiscal_country_id
        WHERE res_country.code = 'EG'
        """
    )
    threshold = env.cr.fetchone()[0]
    if threshold is not None:
        params.set_str("l10n_eg_edi_eta.invoicing_threshold", str(threshold))


def _l10n_eg_edi_eta_submission(env):
    """
    The ETA response of each invoice is now kept in l10n_eg_edi.eta.submission:
    create one submission per invoice sent in 19.0, so that it keeps its state,
    UUID, long ID and QR code and is not sent again
    """
    if not openupgrade.column_exists(
        env.cr, "account_move", "l10n_eg_submission_number"
    ):
        return
    env.cr.execute(
        """
        INSERT INTO l10n_eg_edi_eta_submission (
            move_id, eta_document_uuid, eta_submission_id, state, message,
            create_uid, create_date, write_uid, write_date
        )
        SELECT
            am.id, am.l10n_eg_uuid, am.l10n_eg_submission_number,
            CASE
                WHEN EXISTS (
                    SELECT 1 FROM account_edi_document aed
                    JOIN account_edi_format aef ON aef.id = aed.edi_format_id
                    WHERE aed.move_id = am.id
                        AND aef.code = 'eg_eta'
                        AND aed.state = 'cancelled'
                ) THEN 'cancel'
                WHEN rc.l10n_eg_production_env THEN 'accepted'
                ELSE 'test'
            END,
            pending.error,
            am.write_uid, am.write_date, am.write_uid, am.write_date
        FROM account_move am
        JOIN res_company rc ON rc.id = am.company_id
        LEFT JOIN LATERAL (
            SELECT regexp_replace(aed.error, '<[^>]*>', '', 'g') AS error
            FROM account_edi_document aed
            JOIN account_edi_format aef ON aef.id = aed.edi_format_id
            WHERE aed.move_id = am.id
                AND aef.code = 'eg_eta'
                AND aed.state = 'to_send'
                AND COALESCE(aed.error, '') <> ''
            LIMIT 1
        ) pending ON TRUE
        WHERE COALESCE(am.l10n_eg_uuid, '') <> ''
            AND NOT EXISTS (
                SELECT 1 FROM l10n_eg_edi_eta_submission s
                WHERE s.move_id = am.id
            )
        RETURNING id
        """
    )
    submission_ids = [row[0] for row in env.cr.fetchall()]
    if not submission_ids:
        return
    submissions = env["l10n_eg_edi.eta.submission"].browse(submission_ids)
    for submission in submissions:
        submission._set_eta_long_id_from_response_json()
    moves = submissions.move_id
    moves._compute_l10n_eg_edi_submission_values()
    moves.flush_recordset()


def _account_edi_document_eta(env):
    """
    The 19.0 account.edi.document of the ETA format are copied above: remove
    them, so the ORM can delete the format at the end of the upgrade instead
    of failing on their foreign key
    """
    if not openupgrade.table_exists(env.cr, "account_edi_document"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        DELETE FROM account_edi_document aed
        USING account_edi_format aef
        WHERE aef.id = aed.edi_format_id
            AND aef.code = 'eg_eta'
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _product_product_l10n_eg_eta_code(env)
    _res_company_l10n_eg_edi_api_mode(env)
    _l10n_eg_invoicing_threshold(env)
    _l10n_eg_edi_eta_submission(env)
    _account_edi_document_eta(env)

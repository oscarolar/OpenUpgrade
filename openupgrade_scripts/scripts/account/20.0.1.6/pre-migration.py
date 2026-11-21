# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_model_renames = [
    ("stock_account.stock.valuation.report", "account.stock.valuation.report"),
]

_xmlid_renames = [
    (
        "stock_account.action_report_stock_valuation",
        "account.action_report_stock_valuation",
    ),
    (
        "stock_account.ir_cron_post_stock_valuation",
        "account.ir_cron_post_stock_valuation",
    ),
]

_column_renames = {
    "account_report": [("active", "active_fallback")],
}


def _account_move_review_state(env):
    """
    account.move#checked is replaced by review_state: posted entries that were
    not checked are the ones left to review, the rest never entered a review.
    """
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE account_move
        ADD COLUMN IF NOT EXISTS review_state varchar DEFAULT 'no_review'
        """,
    )
    openupgrade.logged_query(
        env.cr, "ALTER TABLE account_move ALTER COLUMN review_state DROP DEFAULT"
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_move
        SET review_state = 'todo'
        WHERE state = 'posted' AND checked IS NOT TRUE
        """,
    )


def _account_move_document_tax_mode(env):
    """
    Precompute account.move#document_tax_mode from the company setting, as the
    compute does, to avoid the ORM doing it record by record.
    """
    openupgrade.logged_query(
        env.cr,
        "ALTER TABLE account_move ADD COLUMN IF NOT EXISTS document_tax_mode varchar",
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_move am
        SET document_tax_mode = COALESCE(rc.account_price_include, 'tax_excluded')
        FROM res_company rc
        WHERE rc.id = am.company_id
            AND am.move_type IN (
                'out_invoice', 'out_refund', 'out_receipt',
                'in_invoice', 'in_refund', 'in_receipt'
            )
        """,
    )


def _account_move_line_deductible_percentage(env):
    """
    account.move.line#deductible_amount (0-100) becomes deductible_percentage
    (0-1). Only the lines that are not fully deductible are rewritten.
    """
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE account_move_line
        ADD COLUMN IF NOT EXISTS deductible_percentage double precision DEFAULT 1.0
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE account_move_line
        ALTER COLUMN deductible_percentage DROP DEFAULT
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_move_line
        SET deductible_percentage = deductible_amount / 100.0
        WHERE deductible_amount IS NOT NULL AND deductible_amount <> 100
        """,
    )


def _account_payment_state(env):
    """
    account.payment#state: 'paid' is now 'reconciled' and 'in_process' is now
    'paid'.
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_payment
        SET state = CASE state WHEN 'paid' THEN 'reconciled' ELSE 'paid' END
        WHERE state IN ('paid', 'in_process')
        """,
    )


def _account_payment_new_columns(env):
    """
    Create the new stored computed columns of account.payment beforehand:
    commercial_partner_id is filled with SQL, transaction_uuid has an empty
    compute and return_partner_bank_id only matters for new payments.
    """
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE account_payment
        ADD COLUMN IF NOT EXISTS commercial_partner_id int4,
        ADD COLUMN IF NOT EXISTS return_partner_bank_id int4,
        ADD COLUMN IF NOT EXISTS transaction_uuid varchar
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_payment ap
        SET commercial_partner_id = rp.commercial_partner_id
        FROM res_partner rp
        WHERE rp.id = ap.partner_id
        """,
    )


def _account_journal_group_unique_name(env):
    """
    account.journal.group#company_id is gone and the name is now unique across
    companies: disambiguate the duplicated names with the company name.
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_journal_group ajg
        SET name = (
            SELECT jsonb_object_agg(
                t.lang,
                t.value || ' (' || COALESCE(rc.name, ajg.id::varchar) || ')'
            )
            FROM jsonb_each_text(ajg.name) AS t(lang, value)
        )
        FROM account_journal_group ajg0
        LEFT JOIN res_company rc ON rc.id = ajg0.company_id
        WHERE ajg0.id = ajg.id AND EXISTS (
            SELECT 1 FROM account_journal_group other
            WHERE other.id < ajg.id AND other.name = ajg.name
        )
        """,
    )


def _account_reconcile_model_stale_columns(env):
    """
    rule_type, payment_tolerance_type and matching_order were dropped in 19.0
    and come back with other values. A database that went through 18.0 still
    has the old columns: set them aside so the ORM creates the new ones.
    """
    for column in ("rule_type", "payment_tolerance_type", "matching_order"):
        if openupgrade.column_exists(env.cr, "account_reconcile_model", column):
            openupgrade.rename_columns(
                env.cr, {"account_reconcile_model": [(column, None)]}
            )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_models(env.cr, _model_renames)
    openupgrade.rename_xmlids(env.cr, _xmlid_renames)
    openupgrade.rename_columns(env.cr, _column_renames)
    _account_move_review_state(env)
    _account_move_document_tax_mode(env)
    _account_move_line_deductible_percentage(env)
    _account_payment_state(env)
    _account_payment_new_columns(env)
    _account_journal_group_unique_name(env)
    _account_reconcile_model_stale_columns(env)

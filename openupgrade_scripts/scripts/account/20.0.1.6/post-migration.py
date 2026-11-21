# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from openupgradelib import openupgrade

from odoo.orm.commands import Command

_company_defaults = [
    ("expense_account_id", "property_account_expense_categ_id"),
    ("income_account_id", "property_account_income_categ_id"),
    ("account_stock_journal_id", "property_stock_journal"),
    ("account_stock_valuation_id", "property_stock_valuation_account_id"),
    ("cost_method", "property_cost_method"),
    ("inventory_valuation", "property_valuation"),
]


def _account_group_to_parent_account(env):
    """
    account.group is gone: the hierarchy is now made of archived accounts that
    are the parent of the accounts of the group. Create one account per group
    (or reuse the account that already has the prefix as code), link the
    hierarchy and keep the xmlids of the groups on the new accounts.
    """
    if not openupgrade.table_exists(env.cr, "account_group"):
        return
    legacy = openupgrade.get_legacy_name("group_id")
    openupgrade.logged_query(
        env.cr, f"ALTER TABLE account_account ADD COLUMN IF NOT EXISTS {legacy} int4"
    )
    env.cr.execute(
        """
        SELECT
            ag.id,
            ag.company_id,
            COALESCE(
                ag.name->>'en_US',
                (SELECT t.value FROM jsonb_each_text(ag.name) AS t LIMIT 1)
            ),
            ag.code_prefix_start,
            (
                SELECT aa.id FROM account_account aa
                WHERE aa.code_store->>ag.company_id::varchar = ag.code_prefix_start
                ORDER BY aa.id LIMIT 1
            ),
            (
                SELECT aa.account_type FROM account_account aa
                WHERE ag.code_prefix_start <= LEFT(
                        aa.code_store->>ag.company_id::varchar,
                        char_length(ag.code_prefix_start)
                    )
                    AND ag.code_prefix_end >= LEFT(
                        aa.code_store->>ag.company_id::varchar,
                        char_length(ag.code_prefix_end)
                    )
                ORDER BY aa.code_store->>ag.company_id::varchar LIMIT 1
            )
        FROM account_group ag
        ORDER BY ag.company_id, char_length(COALESCE(ag.code_prefix_start, '')), ag.id
        """
    )
    AccountAccount = env["account.account"].with_context(
        tracking_disable=True, mail_create_nolog=True
    )
    created_ids = []
    for group_id, company_id, name, code, existing_id, account_type in env.cr.fetchall():
        account_id = existing_id
        if not account_id:
            account_id = (
                AccountAccount.with_company(company_id)
                .create(
                    {
                        "name": name,
                        "code": re.sub(r"[^A-Za-z0-9.-]", "", code or "") or False,
                        "account_type": account_type or "asset_current",
                        "active": False,
                        "company_ids": [Command.set([company_id])],
                    }
                )
                .id
            )
            created_ids.append(account_id)
        env.cr.execute(
            f"UPDATE account_account SET {legacy} = %s WHERE id = %s",
            (group_id, account_id),
        )
    env["account.account"].flush_model()
    if created_ids:
        openupgrade.logged_query(
            env.cr,
            f"""
            UPDATE account_account aa
            SET name = ag.name
            FROM account_group ag
            WHERE aa.{legacy} = ag.id AND aa.id = ANY(%s)
            """,
            (created_ids,),
        )
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE account_account aa
        SET parent_id = parent.id
        FROM account_group ag
        JOIN account_account parent ON parent.{legacy} = ag.parent_id
        WHERE aa.{legacy} = ag.id AND aa.parent_id IS NULL AND parent.id <> aa.id
        """,
    )
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE account_account aa
        SET parent_id = sub.parent_id
        FROM (
            SELECT DISTINCT ON (child.id) child.id, parent.id AS parent_id
            FROM account_account child
            JOIN account_account_res_company_rel rel
                ON rel.account_account_id = child.id
            JOIN res_company rc ON rc.id = rel.res_company_id
            JOIN account_group ag
                ON ag.company_id = split_part(rc.parent_path, '/', 1)::int4
                AND ag.code_prefix_start <= LEFT(
                    child.code_store->>ag.company_id::varchar,
                    char_length(ag.code_prefix_start)
                )
                AND ag.code_prefix_end >= LEFT(
                    child.code_store->>ag.company_id::varchar,
                    char_length(ag.code_prefix_end)
                )
            JOIN account_account parent ON parent.{legacy} = ag.id
            WHERE child.{legacy} IS NULL AND NOT EXISTS (
                SELECT 1
                FROM account_account_res_company_rel other_rel
                JOIN res_company other ON other.id = other_rel.res_company_id
                WHERE other_rel.account_account_id = child.id
                    AND split_part(other.parent_path, '/', 1)::int4 <> ag.company_id
            )
            ORDER BY
                child.id,
                rel.res_company_id,
                char_length(ag.code_prefix_start) DESC,
                ag.id
        ) sub
        WHERE aa.id = sub.id AND aa.parent_id IS NULL
        """,
    )
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE ir_model_data imd
        SET model = 'account.account', res_id = aa.id
        FROM account_account aa
        WHERE imd.model = 'account.group' AND aa.{legacy} = imd.res_id
        """,
    )
    env["account.account"].invalidate_model()
    env["account.account"]._parent_store_compute()


def _account_journal_group_id(env):
    """
    Ledgers used to list the journals they exclude and now each journal belongs
    to one ledger at most. A journal that was excluded from every ledger of its
    company but one is specific to that one; the journals included in all of
    them stay common to every ledger.
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_journal aj
        SET journal_group_id = sub.group_id
        FROM (
            SELECT aj.id, min(ajg.id) AS group_id
            FROM account_journal aj
            JOIN res_company rc ON rc.id = aj.company_id
            JOIN account_journal_group ajg
                ON ajg.company_id IS NULL
                OR ('/' || rc.parent_path) LIKE ('%%/' || ajg.company_id || '/%%')
            WHERE NOT EXISTS (
                SELECT 1 FROM account_journal_account_journal_group_rel rel
                WHERE rel.account_journal_id = aj.id
                    AND rel.account_journal_group_id = ajg.id
            )
            GROUP BY aj.id
            HAVING count(*) = 1
        ) sub
        WHERE aj.id = sub.id AND aj.journal_group_id IS NULL AND EXISTS (
            SELECT 1 FROM account_journal_account_journal_group_rel rel
            WHERE rel.account_journal_id = aj.id
        )
        """,
    )


def _account_report_line_foldability(env):
    """
    account.report.line#foldable is replaced by the foldability selection
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_report_line
        SET foldability = 'foldable'
        WHERE foldable AND foldability IS DISTINCT FROM 'foldable'
        """,
    )


def _res_company_defaults(env):
    """
    Several res.company fields are no longer stored: they read and write the
    company default (ir.default) of the matching product.category property.
    Create the default from the old column when there is none.
    """
    for company_field, category_field in _company_defaults:
        if not openupgrade.column_exists(env.cr, "res_company", company_field):
            continue
        openupgrade.logged_query(
            env.cr,
            f"""
            INSERT INTO ir_default (
                field_id, company_id, json_value,
                create_uid, write_uid, create_date, write_date
            )
            SELECT
                imf.id, rc.id, to_json(rc.{company_field})::varchar,
                1, 1, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC'
            FROM res_company rc
            JOIN ir_model_fields imf
                ON imf.model = 'product.category' AND imf.name = %s
            WHERE rc.{company_field} IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM ir_default d
                WHERE d.field_id = imf.id
                    AND d.user_id IS NULL
                    AND d.condition IS NULL
                    AND (d.company_id = rc.id OR d.company_id IS NULL)
            )
            """,
            (category_field,),
        )
    env.transaction.invalidate_ormcache()
    env.invalidate_all()


def _account_move_inventory_closing(env):
    """
    The stock closing entries were listed in a system parameter per company and
    are now flagged with account.move#inventory_closing
    """
    openupgrade.logged_query(
        env.cr,
        r"""
        UPDATE account_move
        SET inventory_closing = TRUE
        WHERE id IN (
            SELECT unnest(string_to_array(value, ','))::int4
            FROM ir_config_parameter
            WHERE key ~ '^[0-9]+\.stock_valuation_closing_ids$'
                AND value ~ '^[0-9]+(,[0-9]+)*$'
        )
        """,
    )


def _res_partner_global_location_number(env):
    """
    res.partner#global_location_number (account_add_gln) is now read from
    additional_identifiers
    """
    if not openupgrade.column_exists(env.cr, "res_partner", "global_location_number"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_partner
        SET additional_identifiers =
            jsonb_build_object('EAN_GLN', global_location_number)
            || COALESCE(additional_identifiers, '{}'::jsonb)
        WHERE COALESCE(global_location_number, '') <> ''
        """,
    )


def _res_partner_latam_identification(env):
    """
    l10n_latam.identification.type is gone: res.partner#vat only holds the tax
    id and any other document goes to additional_identifiers. Move the
    passports here; the country specific types are moved by their l10n module.
    """
    if not openupgrade.column_exists(
        env.cr, "res_partner", "l10n_latam_identification_type_id"
    ):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_partner rp
        SET additional_identifiers =
                jsonb_build_object('PASSPORT', rp.vat)
                || COALESCE(rp.additional_identifiers, '{}'::jsonb),
            vat = NULL
        FROM ir_model_data imd
        WHERE imd.model = 'l10n_latam.identification.type'
            AND imd.module IN ('account', 'l10n_latam_base')
            AND imd.name = 'it_pass'
            AND imd.res_id = rp.l10n_latam_identification_type_id
            AND COALESCE(rp.vat, '') <> ''
        """,
    )


def _account_reconcile_model_matching_order(env):
    """
    Restore account.reconcile.model#matching_order when the column survived
    from 18.0, where the field had the same values
    """
    legacy = openupgrade.get_legacy_name("matching_order")
    if not openupgrade.column_exists(env.cr, "account_reconcile_model", legacy):
        return
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE account_reconcile_model
        SET matching_order = {legacy}
        WHERE {legacy} IN ('new_first', 'old_first')
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "account", "20.0.1.6/noupdate_changes.xml")
    openupgrade.delete_record_translations(
        env.cr,
        "account",
        [
            "email_template_edi_invoice",
            "email_template_edi_self_billing_invoice",
            "mail_template_data_payment_receipt",
        ],
        ["body_html"],
    )
    _account_group_to_parent_account(env)
    _account_journal_group_id(env)
    _account_report_line_foldability(env)
    _res_company_defaults(env)
    _account_move_inventory_closing(env)
    _res_partner_global_location_number(env)
    _res_partner_latam_identification(env)
    _account_reconcile_model_matching_order(env)

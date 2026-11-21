# Copyright 2026 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import ast
import csv

from openupgradelib import openupgrade

from odoo.tools import file_open

# pylint: disable=odoo-addons-relative-import
from odoo.addons.openupgrade_scripts.apriori import merged_modules, renamed_modules

_renamed_xmlids = [
    ("website.default_website", "base.default_website"),
    ("l10n_in.state_in_la", "base.state_in_la"),
    ("base.state_in_or", "base.state_in_od"),
]

_copied_columns = {
    "ir_exports_line": [
        ("id", "sequence", None),
    ],
    "res_company": [
        ("font", None, None),
    ],
}

_merged_xmlids = [
    ("base.state_eg_su", "base.state_eg_gz"),
    ("base.state_eg_hu", "base.state_eg_c"),
]

_renamed_columns = {
    "ir_model_fields": [
        ("index", None),
    ],
    "res_partner_bank": [
        ("acc_number", "account_number"),
        ("acc_holder_name", "holder_name"),
        ("sanitized_acc_number", "sanitized_account_number"),
    ],
    "res_device_log": [
        ("browser", "user_agent"),
    ],
}


def _normalize_domain(domain):
    """
    Return a representation of a domain string that does not depend on its formatting
    """
    domain = (domain or "").strip() or "[]"
    try:
        normalized = ast.dump(ast.parse(domain, mode="eval"))
    except SyntaxError:
        return " ".join(domain.split())
    if normalized in (
        ast.dump(ast.parse("[]", mode="eval")),
        ast.dump(ast.parse("[(1, '=', 1)]", mode="eval")),
    ):
        return "TRUE"
    return normalized


def ir_rule_customized(env):
    """
    Store which ir.rule records provided by modules differ from their v19 definition.
    Those were noupdate records the user could change, the end-migration uses this to
    carry the changes over to ir.access.

    This has to run before modules and xmlids are renamed.
    """
    with file_open(
        "openupgrade_scripts/scripts/base/20.0.1.3/ir_rule_19.csv"
    ) as rule_file:
        standard_rules = {row["xmlid"]: row for row in csv.DictReader(rule_file)}
    table = openupgrade.get_legacy_name("ir_rule_customized")
    env.cr.execute(
        f"""
        CREATE TABLE {table} (
            rule_id integer, xmlid varchar, std_domain text, std_active boolean,
            diff_domain boolean, diff_active boolean, diff_perms boolean,
            diff_groups boolean
        )
        """
    )
    env.cr.execute(
        """
        SELECT
            ir_rule.id, ir_model_data.module || '.' || ir_model_data.name AS xmlid,
            ir_rule.active, ir_rule.perm_create, ir_rule.perm_read,
            ir_rule.perm_write, ir_rule.perm_unlink, ir_rule.domain_force,
            COALESCE((
                SELECT
                    string_agg(
                        group_data.module || '.' || group_data.name, ','
                        ORDER BY group_data.module || '.' || group_data.name
                    )
                FROM
                    rule_group_rel
                LEFT JOIN
                    ir_model_data group_data
                ON
                    group_data.model='res.groups'
                    AND group_data.res_id=rule_group_rel.group_id
                WHERE
                    rule_group_rel.rule_group_id=ir_rule.id
            ), '') AS groups,
            (
                SELECT count(*) FROM rule_group_rel
                WHERE rule_group_rel.rule_group_id=ir_rule.id
            ) AS group_count
        FROM
            ir_rule
        JOIN
            ir_model_data
        ON
            ir_model_data.model='ir.rule' AND ir_model_data.res_id=ir_rule.id
        """
    )
    for row in env.cr.dictfetchall():
        standard = standard_rules.get(row["xmlid"])
        if not standard:
            continue
        std_active = standard["active"] == "1"
        diff_domain = _normalize_domain(row["domain_force"]) != _normalize_domain(
            standard["domain"]
        )
        diff_active = row["active"] != std_active
        diff_perms = any(
            row[field_name] != (standard[field_name] == "1")
            for field_name in ("perm_create", "perm_read", "perm_write", "perm_unlink")
        )
        diff_groups = row["groups"] != standard["groups"] or row["group_count"] != (
            len(standard["groups"].split(",")) if standard["groups"] else 0
        )
        if not (diff_domain or diff_active or diff_perms or diff_groups):
            continue
        openupgrade.logged_query(
            env.cr,
            f"""
            INSERT INTO {table} (
                rule_id, xmlid, std_domain, std_active,
                diff_domain, diff_active, diff_perms, diff_groups
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                row["id"],
                row["xmlid"],
                standard["domain"],
                std_active,
                diff_domain,
                diff_active,
                diff_perms,
                diff_groups,
            ),
        )


def ir_model_access_ir_rule_xmlids(env):
    """
    Postfix all xmlids pointing to ir.rule or ir.model.access with their model name to
    avoid clashes from ir.access records with the same name
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_model_data
        SET name=name || '_' || replace(model, '.', '_')
        WHERE
            model IN ('ir.rule', 'ir.model.access')
        AND
            module NOT IN (
                '__export__', '__custom__', 'studio_customization'
            )
        """,
    )


def ir_actions_client(env):
    """
    Change type of ir.actions.client#params_store to text
    """
    env.cr.execute(
        """
        ALTER TABLE
            ir_act_client
        ALTER COLUMN
            params_store
        SET DATA TYPE
            text
        USING
            CONVERT_FROM(params_store, 'utf8')
        """
    )


def res_company(env):
    """
    Map fonts in res.company#font
    """
    openupgrade.map_values(
        env.cr,
        openupgrade.get_legacy_name("font"),
        "font",
        [("Fira_Mono", "Noto_Sans_Mono")],
        table="res_company",
    )


def l10n_eu_account_vies(env):
    """
    base_vat is merged into base, but its VIES validation lives in the new module
    l10n_eu_account_vies. Keep its cron if some company uses VIES validation, the
    module is installed in post-migration
    """
    if not openupgrade.column_exists(env.cr, "res_company", "vat_check_vies"):
        return
    env.cr.execute("SELECT 1 FROM res_company WHERE vat_check_vies LIMIT 1")
    if env.cr.rowcount:
        openupgrade.rename_xmlids(
            env.cr,
            [
                (
                    "base.vies_iap_check_update",
                    "l10n_eu_account_vies.vies_iap_check_update",
                ),
            ],
        )


def res_device_log(env):
    """
    Fill required columns
    """
    openupgrade.lift_constraints(env.cr, "res_device_log", "user_id")
    for column, value in (
        ("first_activity", "create_date"),
        ("ip_address", "'0.0.0.0'"),
        ("last_activity", "create_date"),
        ("user_agent", "'unknown'"),
        ("user_id", -1),
    ):
        openupgrade.logged_query(
            env.cr, f"UPDATE res_device_log SET {column}={value} WHERE {column} IS NULL"
        )


@openupgrade.migrate()
def migrate(env, version):
    ir_rule_customized(env)
    openupgrade.logged_query(
        env.cr,
        f"""
        CREATE TABLE {
            openupgrade.get_legacy_name("ir_module_module")
        } AS (SELECT name, state FROM ir_module_module);
        """,
    )

    openupgrade.update_module_names(
        env.cr, renamed_modules.items(), environment_namespec=True
    )
    openupgrade.update_module_names(
        env.cr, merged_modules.items(), merge_modules=True, environment_namespec=True
    )
    openupgrade.clean_transient_models(env.cr)
    openupgrade.copy_columns(env.cr, _copied_columns)
    openupgrade.rename_xmlids(env.cr, _renamed_xmlids)
    # merge calls get_many2one_references which expects
    # column ir_model_fields.relation_model_field to exist in v20,
    # but this column will only be created during this upgrade.
    # pretend to be 19 just for this call
    version_info_org = openupgrade.version_info
    openupgrade.version_info = (19,)
    openupgrade.rename_xmlids(env.cr, _merged_xmlids, allow_merge=True)
    openupgrade.version_info = version_info_org
    openupgrade.rename_columns(env.cr, _renamed_columns)
    ir_model_access_ir_rule_xmlids(env)
    ir_actions_client(env)
    res_company(env)
    l10n_eu_account_vies(env)
    res_device_log(env)
    openupgrade.set_xml_ids_noupdate_value(
        env, "base", ["module_category_administration"], True
    )

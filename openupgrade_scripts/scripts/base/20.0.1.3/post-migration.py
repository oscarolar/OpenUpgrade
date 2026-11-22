# Copyright 2026 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from openupgradelib import openupgrade
from psycopg2 import sql

from odoo.addons.base.models.ir_model import selection_xmlid

_logger = logging.getLogger(__name__)


def ir_model_fields_index(env):
    """
    Fill index field for custom models
    """
    old_index_field = openupgrade.get_legacy_name("index")
    env.cr.execute(
        f"""
        UPDATE
            ir_model_fields
        SET
            index=CASE WHEN {old_index_field} THEN 'btree' ELSE NULL END
        WHERE
            state='manual'
        """
    )


def res_partner_tz(env):
    """
    Selection source has been changed from pytz.all_timezones (v19) to
    zoneinfo.available_timezones() restricted by babel.dates.get_timezone (v20)

    Map removed values to their most sensible candidate
    """
    openupgrade.copy_columns(
        env.cr,
        {
            "res_partner": [
                ("tz", None, None),
            ],
        },
    )
    mapped_values = [
        ("Europe/Kiev", "Europe/Kyiv"),
        ("Portugal", "Europe/Lisbon"),
        ("Poland", "Europe/Warsaw"),
    ]
    openupgrade.map_values(
        env.cr,
        openupgrade.get_legacy_name("tz"),
        "tz",
        table="res_partner",
        mapping=mapped_values,
    )
    openupgrade.rename_xmlids(
        env.cr,
        [
            (
                selection_xmlid("base", "res.partner", "tz", old_value),
                selection_xmlid("base", "res.partner", "tz", new_value),
            )
            for old_value, new_value in mapped_values
        ],
        allow_merge=True,
    )


def res_partner_bank(env):
    """
    Fill new res.partner.bank fields from res.bank and align the clearing label with
    the country taken from the bank
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            res_partner_bank
        SET
            bank_bic=res_bank.bic,
            city=res_bank.city,
            country_id=COALESCE(res_bank.country, res_partner_bank.country_id),
            bank_name=res_bank.name,
            state_id=res_bank.state,
            street=res_bank.street,
            street2=res_bank.street2,
            zip=res_bank.zip
        FROM
            res_bank
        WHERE
            bank_id=res_bank.id
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            res_partner_bank
        SET
            clearing_label_id=COALESCE(
                (
                    SELECT id FROM clearing_label
                    WHERE clearing_label.country_id=res_partner_bank.country_id
                    ORDER BY id LIMIT 1
                ),
                (
                    SELECT id FROM clearing_label
                    WHERE clearing_label.country_id IS NULL
                    ORDER BY id LIMIT 1
                ),
                clearing_label_id
            )
        WHERE
            bank_id IS NOT NULL
        """,
    )


def res_partner_bank_country(env):
    """
    res.partner.bank#country_id is new: its compute falls back on the country
    of the current company (the main one during the upgrade) when neither the
    partner, the company of the account nor its bank have one. Take instead the
    country of the commercial partner, or of the company that uses the account
    most on journal entries and payments, and give the account the clearing
    label of that country. The main company stays as the last resort
    """
    usages = [
        f"SELECT partner_bank_id, company_id FROM {table} "
        "WHERE partner_bank_id IS NOT NULL"
        for table in ("account_move", "account_payment")
        if openupgrade.column_exists(env.cr, table, "partner_bank_id")
        and openupgrade.column_exists(env.cr, table, "company_id")
    ] or ["SELECT NULL::int AS partner_bank_id, NULL::int AS company_id"]
    env.cr.execute(
        f"""
        WITH usage AS ({" UNION ALL ".join(usages)}),
        usage_country AS (
            SELECT DISTINCT ON (usage.partner_bank_id)
                usage.partner_bank_id, company_partner.country_id
            FROM usage
            JOIN res_company company ON company.id = usage.company_id
            JOIN res_partner company_partner
                ON company_partner.id = company.partner_id
            WHERE company_partner.country_id IS NOT NULL
            GROUP BY usage.partner_bank_id, company_partner.country_id
            ORDER BY usage.partner_bank_id, COUNT(*) DESC,
                company_partner.country_id
        ),
        new AS (
            SELECT rpb.id,
                COALESCE(commercial.country_id, usage_country.country_id)
                    AS country_id
            FROM res_partner_bank rpb
            JOIN res_partner partner ON partner.id = rpb.partner_id
            LEFT JOIN res_partner commercial
                ON commercial.id = partner.commercial_partner_id
            LEFT JOIN res_company company ON company.id = rpb.company_id
            LEFT JOIN res_partner company_partner
                ON company_partner.id = company.partner_id
            LEFT JOIN res_bank bank ON bank.id = rpb.bank_id
            LEFT JOIN usage_country ON usage_country.partner_bank_id = rpb.id
            WHERE partner.country_id IS NULL
                AND company_partner.country_id IS NULL
                AND bank.country IS NULL
        )
        UPDATE res_partner_bank rpb
        SET country_id = new.country_id
        FROM new
        WHERE new.id = rpb.id
            AND new.country_id IS NOT NULL
            AND new.country_id IS DISTINCT FROM rpb.country_id
        RETURNING rpb.id
        """
    )
    account_ids = [row[0] for row in env.cr.fetchall()]
    _logger.info(
        "res.partner.bank: country of %s accounts taken from their commercial "
        "partner or the company using them",
        len(account_ids),
    )
    if not account_ids:
        return account_ids
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_partner_bank rpb
        SET clearing_label_id = COALESCE(
            (
                SELECT id FROM clearing_label
                WHERE clearing_label.country_id = rpb.country_id
                ORDER BY id LIMIT 1
            ),
            (
                SELECT id FROM clearing_label
                WHERE clearing_label.country_id IS NULL
                ORDER BY id LIMIT 1
            ),
            rpb.clearing_label_id
        )
        WHERE rpb.id = ANY(%s)
        """,
        (account_ids,),
    )
    return account_ids


def res_partner(env):
    """
    Fill additional_identifiers from company_registry
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            res_partner
        SET
            additional_identifiers=COALESCE(
                additional_identifiers, jsonb_build_object()
            ) || jsonb_build_object('OTHER', company_registry)
        WHERE
            company_registry IS NOT NULL
        """,
    )


def res_country_zip_applicability(env):
    """
    Keep the zip code optional for countries where it was not required
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            res_country
        SET
            zip_applicability='optional'
        WHERE
            zip_required IS NOT TRUE
        AND
            zip_applicability='required'
        """,
    )


def res_groups(env):
    """
    Add all members of group_user to group_user_regular
    """
    openupgrade.logged_query(
        env.cr,
        f"""
        INSERT INTO
            res_groups_users_rel
            (uid, gid)
        SELECT
            uid, {env.ref("base.group_user_regular").id}
        FROM
            res_groups_users_rel
        WHERE
            gid={env.ref("base.group_user").id}
        AND NOT EXISTS (
            SELECT uid FROM res_groups_users_rel res_groups_users_rel2
            WHERE gid={env.ref("base.group_system").id}
            AND uid=res_groups_users_rel.uid
        )
        """,
    )


def res_users_apikeys_scope(env):
    """
    Set scope rpc for apikeys with scope null
    """
    openupgrade.logged_query(
        env.cr, "UPDATE res_users_apikeys SET scope='rpc' WHERE scope IS NULL"
    )


def ir_config_parameter_default_max_email_size(env):
    """
    Preserve custom default_max_email_size or ir.mail_server#max_email_size,
    whichever is lowest. Set new default 20 otherwise
    """
    IrConfigParameter = env["ir.config_parameter"]
    key = "base.default_max_email_size"
    config_param_value = IrConfigParameter.get_float(key, 10)
    env.cr.execute(
        f"""
        SELECT
            MIN(
                CASE
                    WHEN max_email_size > 0 THEN max_email_size
                    ELSE {config_param_value}
                END
            )
        FROM
            ir_mail_server
        WHERE
            active
        """
    )
    least_value = 0
    for row in env.cr.fetchall():
        least_value = row[0]
    if least_value and least_value != 10:
        IrConfigParameter.set_float(key, least_value)
    else:
        IrConfigParameter.set_float(key, 20)


def l10n_eu_account_vies(env):
    """
    Install l10n_eu_account_vies if some company uses VIES validation, which was part
    of base_vat
    """
    if not openupgrade.column_exists(env.cr, "res_company", "vat_check_vies"):
        return
    env.cr.execute("SELECT 1 FROM res_company WHERE vat_check_vies LIMIT 1")
    if not env.cr.rowcount:
        return
    IrModuleModule = env["ir.module.module"]
    IrModuleModule.update_list()
    IrModuleModule.search(
        [("name", "=", "l10n_eu_account_vies"), ("state", "=", "uninstalled")]
    ).button_install()


_merged_sa_states = [
    ("base.state_sa_1", "base.state_sa_014"),
    ("base.state_sa_2", "base.state_sa_004"),
    ("base.state_sa_3", "base.state_sa_004"),
    ("base.state_sa_4", "base.state_sa_001"),
    ("base.state_sa_5", "base.state_sa_011"),
    ("base.state_sa_6", "base.state_sa_011"),
    ("base.state_sa_7", "base.state_sa_002"),
    ("base.state_sa_8", "base.state_sa_012"),
    ("base.state_sa_9", "base.state_sa_004"),
    ("base.state_sa_10", "base.state_sa_012"),
    ("base.state_sa_11", "base.state_sa_004"),
    ("base.state_sa_12", "base.state_sa_001"),
    ("base.state_sa_13", "base.state_sa_004"),
    ("base.state_sa_14", "base.state_sa_004"),
    ("base.state_sa_16", "base.state_sa_004"),
    ("base.state_sa_17", "base.state_sa_014"),
    ("base.state_sa_18", "base.state_sa_002"),
    ("base.state_sa_20", "base.state_sa_009"),
    ("base.state_sa_21", "base.state_sa_004"),
    ("base.state_sa_22", "base.state_sa_005"),
    ("base.state_sa_23", "base.state_sa_008"),
    ("base.state_sa_24", "base.state_sa_002"),
    ("base.state_sa_25", "base.state_sa_008"),
    ("base.state_sa_26", "base.state_sa_014"),
    ("base.state_sa_27", "base.state_sa_005"),
    ("base.state_sa_28", "base.state_sa_005"),
    ("base.state_sa_29", "base.state_sa_004"),
    ("base.state_sa_30", "base.state_sa_007"),
    ("base.state_sa_32", "base.state_sa_005"),
    ("base.state_sa_33", "base.state_sa_012"),
    ("base.state_sa_34", "base.state_sa_004"),
    ("base.state_sa_35", "base.state_sa_006"),
    ("base.state_sa_36", "base.state_sa_004"),
    ("base.state_sa_37", "base.state_sa_008"),
    ("base.state_sa_38", "base.state_sa_004"),
    ("base.state_sa_39", "base.state_sa_009"),
    ("base.state_sa_40", "base.state_sa_002"),
    ("base.state_sa_41", "base.state_sa_002"),
    ("base.state_sa_42", "base.state_sa_002"),
    ("base.state_sa_43", "base.state_sa_009"),
    ("base.state_sa_44", "base.state_sa_012"),
    ("base.state_sa_45", "base.state_sa_004"),
    ("base.state_sa_46", "base.state_sa_004"),
    ("base.state_sa_47", "base.state_sa_014"),
    ("base.state_sa_48", "base.state_sa_002"),
    ("base.state_sa_51", "base.state_sa_002"),
    ("base.state_sa_52", "base.state_sa_003"),
    ("base.state_sa_53", "base.state_sa_001"),
    ("base.state_sa_54", "base.state_sa_002"),
    ("base.state_sa_56", "base.state_sa_001"),
    ("base.state_sa_57", "base.state_sa_014"),
    ("base.state_sa_58", "base.state_sa_010"),
    ("base.state_sa_59", "base.state_sa_010"),
    ("base.state_sa_60", "base.state_sa_004"),
    ("base.state_sa_62", "base.state_sa_004"),
    ("base.state_sa_63", "base.state_sa_004"),
    ("base.state_sa_64", "base.state_sa_002"),
    ("base.state_sa_65", "base.state_sa_008"),
    ("base.state_sa_66", "base.state_sa_004"),
    ("base.state_sa_67", "base.state_sa_004"),
    ("base.state_sa_68", "base.state_sa_004"),
    ("base.state_sa_69", "base.state_sa_004"),
    ("base.state_sa_70", "base.state_sa_001"),
    ("base.state_sa_71", "base.state_sa_001"),
    ("base.state_sa_72", "base.state_sa_004"),
    ("base.state_sa_73", "base.state_sa_001"),
    ("base.state_sa_74", "base.state_sa_004"),
    ("base.state_sa_75", "base.state_sa_004"),
    ("base.state_sa_76", "base.state_sa_004"),
    ("base.state_sa_77", "base.state_sa_010"),
    ("base.state_sa_78", "base.state_sa_002"),
    ("base.state_sa_79", "base.state_sa_001"),
    ("base.state_sa_80", "base.state_sa_007"),
    ("base.state_sa_81", "base.state_sa_002"),
    ("base.state_sa_82", "base.state_sa_008"),
    ("base.state_sa_84", "base.state_sa_004"),
    ("base.state_sa_85", "base.state_sa_007"),
    ("base.state_sa_86", "base.state_sa_005"),
    ("base.state_sa_87", "base.state_sa_001"),
    ("base.state_sa_89", "base.state_sa_007"),
    ("base.state_sa_90", "base.state_sa_003"),
    ("base.state_sa_91", "base.state_sa_003"),
    ("base.state_sa_92", "base.state_sa_001"),
]


def res_country_state_merged_references(cr, xmlids_spec):
    """
    Merging states repoints the foreign keys, but not the defaults (ir.default)
    that store the id of a merged state, and it fails on every many2many row
    that already links the target state (a fiscal position or a delivery method
    with several cities of the same province): move those first
    """
    cr.execute(
        """
        SELECT kcu.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON kcu.constraint_name = tc.constraint_name
            AND kcu.table_schema = tc.table_schema
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND ccu.table_name = 'res_country_state'
            AND ccu.column_name = 'id'
        """
    )
    relations = []
    for table, column in cr.fetchall():
        cr.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
            (table,),
        )
        columns = [row[0] for row in cr.fetchall()]
        if len(columns) == 2 and "id" not in columns:
            relations.append((table, column, next(c for c in columns if c != column)))
    for old, new in xmlids_spec:
        cr.execute(
            """
            SELECT old.res_id, new.res_id
            FROM ir_model_data old, ir_model_data new
            WHERE old.module = %s AND old.name = %s
                AND new.module = %s AND new.name = %s
                AND old.model = 'res.country.state'
                AND new.model = 'res.country.state'
            """,
            tuple(old.split(".") + new.split(".")),
        )
        row = cr.fetchone()
        if not row:
            continue
        params = {"old": row[0], "new": row[1]}
        openupgrade.logged_query(
            cr,
            """
            UPDATE ir_default
            SET json_value = %(new)s::text
            FROM ir_model_fields imf
            WHERE imf.id = ir_default.field_id
                AND imf.relation = 'res.country.state'
                AND imf.ttype = 'many2one'
                AND ir_default.json_value = %(old)s::text
            """,
            params,
        )
        for table, column, other in relations:
            openupgrade.logged_query(
                cr,
                sql.SQL(
                    """
                    INSERT INTO {table} ({other}, {column})
                    SELECT {other}, %(new)s FROM {table} WHERE {column} = %(old)s
                    ON CONFLICT DO NOTHING
                    """
                ).format(
                    table=sql.Identifier(table),
                    column=sql.Identifier(column),
                    other=sql.Identifier(other),
                ),
                params,
            )
            openupgrade.logged_query(
                cr,
                sql.SQL("DELETE FROM {table} WHERE {column} = %(old)s").format(
                    table=sql.Identifier(table), column=sql.Identifier(column)
                ),
                params,
            )


_unmerged_sa_states = [
    "state_sa_15",
    "state_sa_19",
    "state_sa_31",
    "state_sa_49",
    "state_sa_50",
    "state_sa_55",
    "state_sa_61",
    "state_sa_83",
    "state_sa_88",
    "state_sa_93",
]

_merged_l10n_states = [
    ("l10n_om.state_om_01", "base.state_om_mu"),
    ("l10n_om.state_om_02", "base.state_om_bu"),
    ("l10n_om.state_om_03", "base.state_om_bs"),
    ("l10n_om.state_om_04", "base.state_om_bj"),
    ("l10n_om.state_om_05", "base.state_om_ma"),
    ("l10n_om.state_om_06", "base.state_om_za"),
    ("l10n_om.state_om_07", "base.state_om_da"),
    ("l10n_om.state_om_08", "base.state_om_ss"),
    ("l10n_om.state_om_09", "base.state_om_sj"),
    ("l10n_om.state_om_10", "base.state_om_wu"),
    ("l10n_om.state_om_11", "base.state_om_zu"),
    ("l10n_bh.state_bh_1", "base.state_bh_13"),
    ("l10n_bh.state_bh_3", "base.state_bh_15"),
    ("l10n_bh.state_bh_4", "base.state_bh_17"),
    ("l10n_bh.state_bh_5", "base.state_bh_14"),
    ("l10n_lb_account.state_lb_01", "base.state_lb_ak"),
    ("l10n_lb_account.state_lb_02_ar", "base.state_lb_ak"),
    ("l10n_lb_account.state_lb_03", "base.state_lb_bh"),
    ("l10n_lb_account.state_lb_04_ar", "base.state_lb_bh"),
    ("l10n_lb_account.state_lb_05", "base.state_lb_ba"),
    ("l10n_lb_account.state_lb_06_ar", "base.state_lb_ba"),
    ("l10n_lb_account.state_lb_07", "base.state_lb_bi"),
    ("l10n_lb_account.state_lb_08_ar", "base.state_lb_bi"),
    ("l10n_lb_account.state_lb_09", "base.state_lb_jl"),
    ("l10n_lb_account.state_lb_10_ar", "base.state_lb_jl"),
    ("l10n_lb_account.state_lb_11", "base.state_lb_as"),
    ("l10n_lb_account.state_lb_12_ar", "base.state_lb_as"),
    ("l10n_lb_account.state_lb_13", "base.state_lb_na"),
    ("l10n_lb_account.state_lb_14_ar", "base.state_lb_na"),
    ("l10n_lb_account.state_lb_15", "base.state_lb_ja"),
    ("l10n_lb_account.state_lb_16_ar", "base.state_lb_ja"),
]


def res_country_state_sa(env):
    """
    The Saudi cities of 19.0 are replaced by the 13 provinces: merge each city
    into its province, so partners and addresses keep a valid state. The
    cities without a known province stay while partners use them: the ORM
    would fail to delete them (an ERROR per city), so they become noupdate
    """
    res_country_state_merged_references(env.cr, _merged_sa_states)
    openupgrade.rename_xmlids(env.cr, _merged_sa_states, allow_merge=True)
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_model_data imd
        SET noupdate = TRUE
        WHERE imd.module = 'base'
            AND imd.name IN %(names)s
            AND EXISTS (
                SELECT 1 FROM res_partner rp WHERE rp.state_id = imd.res_id
            )
        """,
        {"names": tuple(_unmerged_sa_states)},
    )


def res_country_state_l10n(env):
    """
    The states of Oman, Bahrain and Lebanon move from l10n_om, l10n_bh and
    l10n_lb_account to base with new codes: merge them into the base states
    before the ORM deletes them (and their links to fiscal positions, delivery
    methods or country groups)
    """
    res_country_state_merged_references(env.cr, _merged_l10n_states)
    openupgrade.rename_xmlids(env.cr, _merged_l10n_states, allow_merge=True)


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(
        env,
        "base",
        "20.0.1.3/noupdate_changes.xml",
        xml_transformation_filename="20.0.1.3/noupdate_changes-transformation.xml",
    )
    openupgrade.delete_records_safely_by_xml_id(
        env,
        [
            "base.transifex_code_translation_reload",
            "base.transifex_code_translation_reload_ir_actions_server",
            "base.transifex_project_url",
        ],
    )
    res_partner_tz(env)
    ir_model_fields_index(env)
    res_partner_bank(env)
    res_partner_bank_country(env)
    res_partner(env)
    res_country_zip_applicability(env)
    res_groups(env)
    res_users_apikeys_scope(env)
    ir_config_parameter_default_max_email_size(env)
    l10n_eu_account_vies(env)
    res_country_state_sa(env)
    res_country_state_l10n(env)

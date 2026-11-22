# Copyright 2026 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

from odoo.addons.base.models.ir_model import selection_xmlid


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


def res_country_state_sa(env):
    """
    The Saudi cities of 19.0 are replaced by the 13 provinces: merge each city
    into its province, so partners and addresses keep a valid state
    """
    openupgrade.rename_xmlids(env.cr, _merged_sa_states, allow_merge=True)


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
    res_partner(env)
    res_country_zip_applicability(env)
    res_groups(env)
    res_users_apikeys_scope(env)
    ir_config_parameter_default_max_email_size(env)
    l10n_eu_account_vies(env)
    res_country_state_sa(env)

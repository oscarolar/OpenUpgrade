# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_industry_sic_groups = {
    "crm_iap_mine_industry_30_155": (
        23,
        25,
        31,
        37,
        52,
        53,
        55,
        56,
        57,
        58,
        59,
        70,
        72,
        79,
    ),
    "crm_iap_mine_industry_33_legacy": (20, 21, 54),
    "crm_iap_mine_industry_69_157": (60, 61, 63, 64),
    "crm_iap_mine_industry_86_legacy": (27, 48, 78),
    "crm_iap_mine_industry_136": (40, 41, 42, 44, 45, 47),
    "crm_iap_mine_industry_138_156": (12, 13, 29, 46, 49),
    "crm_iap_mine_industry_148": (10, 14, 24, 26, 28, 30, 32, 33),
    "crm_iap_mine_industry_149": (48,),
    "crm_iap_mine_industry_150_151": (58, 70, 72, 79, 82),
    "crm_iap_mine_industry_152": (52, 53, 55, 56, 57, 59),
    "crm_iap_mine_industry_153_154": (20, 21),
    "crm_iap_mine_industry_158_159": (61, 62, 67),
    "crm_iap_mine_industry_160": (38, 80),
    "crm_iap_mine_industry_161": (28,),
    "crm_iap_mine_industry_162": (15, 16, 17, 34, 35, 36, 37),
    "crm_iap_mine_industry_163": (73, 81, 87),
    "crm_iap_mine_industry_165": (73,),
    "crm_iap_mine_industry_166": (35, 36),
    "crm_iap_mine_industry_167": (32,),
    "crm_iap_mine_industry_168": (49,),
    "crm_iap_mine_industry_238": (37,),
    "crm_iap_mine_industry_239": (23, 25, 31),
}

_industry_relations = [
    (
        "crm_iap_lead_industry_crm_iap_lead_mining_request_rel",
        "crm_iap_lead_mining_request_id",
    ),
    ("crm_iap_lead_industry_crm_reveal_rule_rel", "crm_reveal_rule_id"),
]


def crm_iap_lead_industry(env):
    """
    Replace the v19 industries in mining requests and reveal rules by the v20
    industries (SIC major groups) that cover them, then delete the v19 industries
    """
    relations = [
        (table, column)
        for table, column in _industry_relations
        if openupgrade.table_exists(env.cr, table)
    ]
    for name, sic_groups in _industry_sic_groups.items():
        industry = env.ref(f"crm_iap_mine.{name}", raise_if_not_found=False)
        if not industry:
            continue
        for table, column in relations:
            openupgrade.logged_query(
                env.cr,
                f"""
                INSERT INTO {table} ({column}, crm_iap_lead_industry_id)
                SELECT rel.{column}, industry.id
                FROM {table} rel, crm_iap_lead_industry industry
                WHERE rel.crm_iap_lead_industry_id=%s
                AND industry.sic_group IN %s
                ON CONFLICT DO NOTHING
                """,
                (industry.id, sic_groups),
            )
    openupgrade.delete_records_safely_by_xml_id(
        env, [f"crm_iap_mine.{name}" for name in _industry_sic_groups]
    )


def crm_iap_lead_industry_required(env):
    """
    Industries created by the user have no SIC group nor division, which are
    required now: classify them as nonclassifiable establishments. Then set the
    constraints that could not be set while the v19 industries existed
    """
    default_industry = env.ref("crm_iap_mine.crm_iap_mine_industry_99")
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE crm_iap_lead_industry
        SET
            sic_group=COALESCE(sic_group, %(sic_group)s),
            division_id=COALESCE(division_id, %(division_id)s)
        WHERE sic_group IS NULL OR division_id IS NULL
        """,
        {
            "sic_group": default_industry.sic_group,
            "division_id": default_industry.division_id.id,
        },
    )
    env["crm.iap.lead.industry"].invalidate_model(["sic_group", "division_id"])
    for column in ("sic_group", "division_id"):
        openupgrade.logged_query(
            env.cr,
            f"ALTER TABLE crm_iap_lead_industry ALTER COLUMN {column} SET NOT NULL",
        )


@openupgrade.migrate()
def migrate(env, version):
    crm_iap_lead_industry(env)
    crm_iap_lead_industry_required(env)

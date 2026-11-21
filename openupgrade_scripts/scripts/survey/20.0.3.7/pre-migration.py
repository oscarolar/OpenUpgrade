# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def survey_survey_certification_report_layout(env):
    """
    Certification layouts lost their fixed colors (purple, blue, gold) in favour of
    the company colors or black: map the old keys to the closest new layout
    """
    openupgrade.copy_columns(
        env.cr,
        {
            "survey_survey": [
                ("certification_report_layout", None, None),
            ],
        },
    )
    openupgrade.map_values(
        env.cr,
        openupgrade.get_legacy_name("certification_report_layout"),
        "certification_report_layout",
        [
            ("modern_purple", "modern_company"),
            ("modern_blue", "modern_company"),
            ("modern_gold", "modern_company"),
            ("classic_purple", "classic-1_company"),
            ("classic_blue", "classic-1_company"),
            ("classic_gold", "classic-1_company"),
        ],
        table="survey_survey",
    )


@openupgrade.migrate()
def migrate(env, version):
    survey_survey_certification_report_layout(env)

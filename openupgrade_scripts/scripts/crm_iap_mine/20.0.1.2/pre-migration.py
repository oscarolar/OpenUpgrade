# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_xmlids = [
    (
        "crm_iap_mine.crm_iap_mine_industry_114",
        "crm_iap_mine.crm_iap_mine_industry_65",
    ),
    (
        "crm_iap_mine.crm_iap_mine_industry_33",
        "crm_iap_mine.crm_iap_mine_industry_33_legacy",
    ),
    (
        "crm_iap_mine.crm_iap_mine_industry_86",
        "crm_iap_mine.crm_iap_mine_industry_86_legacy",
    ),
]


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_xmlids(env.cr, _renamed_xmlids)

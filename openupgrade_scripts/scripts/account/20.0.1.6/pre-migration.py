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


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_models(env.cr, _model_renames)
    openupgrade.rename_xmlids(env.cr, _xmlid_renames)

# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

# pylint: disable=odoo-addons-relative-import
from odoo.addons.openupgrade_scripts.l10n_tax_tags import migrate_obsolete_tax_tags

_obsolete_reports = (
    "tax_report_other_taxes",
    "tax_report_schedule_tax",
)
_obsolete_expressions = (
    "tax_report_vat_return_expense_base_exempt_tag",
    "tax_report_vat_return_expense_base_fourteen_tag",
    "tax_report_vat_return_expense_base_zero_tag",
    "tax_report_vat_return_expense_tax_exempt_tag",
    "tax_report_vat_return_expense_tax_fourteen_tag",
    "tax_report_vat_return_expense_tax_zero_tag",
    "tax_report_vat_return_sale_base_exempt_tag",
    "tax_report_vat_return_sale_base_fourteen_tag",
    "tax_report_vat_return_sale_base_zero_tag",
    "tax_report_vat_return_sale_tax_exempt_tag",
    "tax_report_vat_return_sale_tax_fourteen_tag",
    "tax_report_vat_return_sale_tax_zero_tag",
    "tax_report_withholding_tax_purchase_base_five_tag",
    "tax_report_withholding_tax_purchase_base_half_tag",
    "tax_report_withholding_tax_purchase_base_one_tag",
    "tax_report_withholding_tax_purchase_base_three_tag",
    "tax_report_withholding_tax_purchase_tax_five_tag",
    "tax_report_withholding_tax_purchase_tax_half_tag",
    "tax_report_withholding_tax_purchase_tax_one_tag",
    "tax_report_withholding_tax_purchase_tax_three_tag",
    "tax_report_withholding_tax_sale_base_five_tag",
    "tax_report_withholding_tax_sale_base_half_tag",
    "tax_report_withholding_tax_sale_base_one_tag",
    "tax_report_withholding_tax_sale_base_three_tag",
    "tax_report_withholding_tax_sale_tax_five_tag",
    "tax_report_withholding_tax_sale_tax_half_tag",
    "tax_report_withholding_tax_sale_tax_one_tag",
    "tax_report_withholding_tax_sale_tax_three_tag",
)


def _tax_tags(env):
    """
    The VAT return gets new tags and the other taxes and schedule tax reports
    are dropped: the VAT taxes of the template take the new tags, the stamp,
    schedule and withholding taxes keep theirs
    """
    return migrate_obsolete_tax_tags(
        env,
        "l10n_eg",
        ("eg",),
        reports=_obsolete_reports,
        expressions=_obsolete_expressions,
    )


@openupgrade.migrate()
def migrate(env, version):
    _tax_tags(env)

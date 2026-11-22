# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_fields = [
    (
        "account.tax",
        "account_tax",
        "is_withholding_tax_on_payment",
        "is_withholding_tax",
    ),
]


@openupgrade.migrate()
def migrate(env, version):
    if openupgrade.column_exists(
        env.cr, "account_tax", "is_withholding_tax_on_payment"
    ) and not openupgrade.column_exists(env.cr, "account_tax", "is_withholding_tax"):
        openupgrade.rename_fields(env, _renamed_fields)

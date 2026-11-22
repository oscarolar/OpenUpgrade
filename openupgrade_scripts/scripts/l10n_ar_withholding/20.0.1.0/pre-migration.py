# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_field_renames = [
    ("account.tax", "account_tax", "l10n_ar_tax_type", "l10n_ar_withholding_tax_type"),
]


@openupgrade.migrate()
def migrate(env, version):
    if openupgrade.column_exists(env.cr, "account_tax", "l10n_ar_tax_type"):
        openupgrade.rename_fields(env, _field_renames)

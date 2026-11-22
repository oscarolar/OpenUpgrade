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


def _account_tax_is_withholding_tax(env):
    if openupgrade.column_exists(
        env.cr, "account_tax", "is_withholding_tax_on_payment"
    ) and not openupgrade.column_exists(env.cr, "account_tax", "is_withholding_tax"):
        openupgrade.rename_fields(env, _renamed_fields)


def _account_move_withholding_amounts(env):
    """
    Create the new stored computed fields of account.move with their value for
    moves without withholding taxes, so that the ORM doesn't compute them on
    every journal entry. The post-migration computes the others
    """
    for column in (
        "withholding_total_amount_currency",
        "withholding_deducted_amount_currency",
    ):
        if openupgrade.column_exists(env.cr, "account_move", column):
            continue
        openupgrade.logged_query(
            env.cr, f"ALTER TABLE account_move ADD COLUMN {column} numeric DEFAULT 0"
        )
        openupgrade.logged_query(
            env.cr, f"ALTER TABLE account_move ALTER COLUMN {column} DROP DEFAULT"
        )


@openupgrade.migrate()
def migrate(env, version):
    _account_tax_is_withholding_tax(env)
    _account_move_withholding_amounts(env)

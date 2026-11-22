# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _account_payment_withhold(env):
    """
    account.payment#should_withhold_tax becomes the withhold selection: a 19.0
    payment that withheld taxes also paid the net amount
    """
    if not openupgrade.column_exists(env.cr, "account_payment", "should_withhold_tax"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_payment
        SET withhold = 'withhold_pay'
        WHERE should_withhold_tax
            AND withhold IS DISTINCT FROM 'withhold_pay'
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _account_payment_withhold(env)

from openupgradelib import openupgrade


def iap_account_balance_amount(env):
    """
    Fill balance_amount from the numeric part of the former stored balance,
    which was formatted as '<amount> <unit name>'
    """
    if not openupgrade.column_exists(env.cr, "iap_account", "balance"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            iap_account
        SET
            balance_amount=
                substring(balance from '^-?[0-9]+[.]?[0-9]*')::double precision
        WHERE
            balance ~ '^-?[0-9]'
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    iap_account_balance_amount(env)

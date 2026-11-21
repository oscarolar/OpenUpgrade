from openupgradelib import openupgrade


def pos_payment_method_payment_provider(env):
    """
    Selection value glory_cash of pos.payment.method#payment_method_type is the
    type cash_machine with payment_provider glory now
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE pos_payment_method
        SET payment_method_type = 'cash_machine', payment_provider = 'glory'
        WHERE payment_method_type = 'glory_cash'
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    pos_payment_method_payment_provider(env)

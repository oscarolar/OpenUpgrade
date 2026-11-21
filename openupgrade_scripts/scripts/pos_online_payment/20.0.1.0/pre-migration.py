from openupgradelib import openupgrade


def pos_payment_method_type(env):
    """
    pos.payment.method#is_online_payment is the value online of
    pos.payment.method#type now
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE pos_payment_method
        SET type = 'online'
        WHERE is_online_payment
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    pos_payment_method_type(env)

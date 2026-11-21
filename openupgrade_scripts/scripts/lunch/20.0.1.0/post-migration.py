# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def lunch_24_hours(env):
    """
    Times are now stored in 24 hours format instead of 12 hours with a moment (am/pm),
    the moment is set to 'am' so that a second run does not add 12 hours again
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            lunch_alert
        SET
            notification_time=LEAST(notification_time + 12, 24),
            notification_moment='am'
        WHERE
            notification_moment='pm'
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            lunch_supplier
        SET
            automatic_email_time=LEAST(automatic_email_time + 12, 24),
            moment='am'
        WHERE
            moment='pm'
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    lunch_24_hours(env)

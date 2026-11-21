from openupgradelib import openupgrade


def calendar_user_google_sync(env):
    """
    Move the events sync token of the primary Google calendar from
    res.users.settings to the primary calendar of the user and enable the
    synchronization there. In v20, res.users.settings#google_calendar_sync_token
    holds the sync token of the calendar list instead, so reset it
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            calendar_user
        SET
            google_sync_enabled=TRUE,
            google_sync_token=res_users_settings.google_calendar_sync_token
        FROM
            res_users_settings
        WHERE
            res_users_settings.user_id=calendar_user.user_id
        AND
            calendar_user.is_primary
        AND
            calendar_user.access_role='owner'
        AND
            res_users_settings.google_calendar_rtoken IS NOT NULL
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            res_users_settings
        SET
            google_calendar_sync_token=NULL
        WHERE
            google_calendar_sync_token IS NOT NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    calendar_user_google_sync(env)

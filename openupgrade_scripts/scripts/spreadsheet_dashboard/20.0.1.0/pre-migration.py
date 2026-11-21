from openupgradelib import openupgrade


def spreadsheet_dashboard_share_name(env):
    """
    The name of a share was related to the name of its dashboard, now it is
    stored and computed as '<dashboard name> - Share Link'
    """
    openupgrade.add_columns(
        env,
        [
            (
                "spreadsheet.dashboard.share",
                "name",
                "char",
                None,
                "spreadsheet_dashboard_share",
            )
        ],
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            spreadsheet_dashboard_share
        SET
            name=(spreadsheet_dashboard.name->>'en_US') || ' - Share Link'
        FROM
            spreadsheet_dashboard
        WHERE
            spreadsheet_dashboard.id=spreadsheet_dashboard_share.dashboard_id
        AND
            spreadsheet_dashboard_share.name IS NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    spreadsheet_dashboard_share_name(env)

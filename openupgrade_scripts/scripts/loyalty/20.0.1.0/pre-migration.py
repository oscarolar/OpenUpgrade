from openupgradelib import openupgrade


def loyalty_history_points_changed_date(env):
    """
    Create the new required column and fill it with the creation date
    """
    openupgrade.add_columns(
        env,
        [
            (
                "loyalty.history",
                "points_changed_date",
                "datetime",
                None,
                "loyalty_history",
            )
        ],
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            loyalty_history
        SET
            points_changed_date=COALESCE(create_date, NOW() AT TIME ZONE 'UTC')
        WHERE
            points_changed_date IS NULL
        """,
    )


def loyalty_history_issued_used(env):
    """
    In v20 a history line either awards or consumes points and both amounts
    must be positive. Move negative amounts to the opposite column and split
    lines doing both in an awarding line and a consuming line
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            loyalty_history
        SET
            issued=
                GREATEST(COALESCE(issued, 0), 0) + GREATEST(-COALESCE(used, 0), 0),
            used=
                GREATEST(COALESCE(used, 0), 0) + GREATEST(-COALESCE(issued, 0), 0)
        WHERE
            issued < 0 OR used < 0
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO loyalty_history (
            card_id, description, issued, used, order_model, order_id,
            points_changed_date, create_uid, create_date, write_uid, write_date
        )
        SELECT
            card_id, description, 0, used, order_model, order_id,
            points_changed_date, create_uid, create_date, write_uid, write_date
        FROM
            loyalty_history
        WHERE
            issued > 0 AND used > 0
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            loyalty_history
        SET
            used=0
        WHERE
            issued > 0 AND used > 0
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    loyalty_history_points_changed_date(env)
    loyalty_history_issued_used(env)

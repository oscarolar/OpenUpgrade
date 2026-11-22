# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_fields = [
    (
        "purchase.order.line",
        "purchase_order_line",
        "location_final_id",
        "forecasted_location_id",
    ),
]

_added_columns = [
    ("purchase.order", "date_promised", "datetime"),
    ("purchase.order.line", "date_promised", "datetime"),
]


def date_promised(env):
    """
    The promised date is set from the planned date when an order is confirmed, and
    it replaces the planned date for the on-time rate of the vendors, so fill it
    for the confirmed orders. The lines are filled with one rewrite of the table
    instead of an UPDATE of almost every row
    """
    if openupgrade.column_exists(env.cr, "purchase_order_line", "date_promised"):
        return
    openupgrade.add_columns(env, _added_columns)
    openupgrade.logged_query(
        env.cr,
        """
        CREATE FUNCTION pg_temp.openupgrade_purchase_order_state(order_id integer)
        RETURNS varchar LANGUAGE sql STABLE AS $$
            SELECT state FROM purchase_order WHERE id=order_id
        $$
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE
            purchase_order_line
        ALTER COLUMN
            date_promised
        TYPE
            timestamp
        USING
            CASE
                WHEN
                    display_type IS NULL
                AND
                    pg_temp.openupgrade_purchase_order_state(order_id)='purchase'
                THEN
                    date_planned
            END
        """,
    )
    openupgrade.logged_query(
        env.cr, "DROP FUNCTION pg_temp.openupgrade_purchase_order_state(integer)"
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            purchase_order
        SET
            date_promised=order_lines.date_promised
        FROM (
            SELECT
                order_id, MIN(date_promised) AS date_promised
            FROM
                purchase_order_line
            WHERE
                display_type IS NULL
            AND
                date_promised IS NOT NULL
            GROUP BY
                order_id
        ) order_lines
        WHERE
            order_lines.order_id=purchase_order.id
        AND
            purchase_order.state='purchase'
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_fields(env, _renamed_fields)
    date_promised(env)

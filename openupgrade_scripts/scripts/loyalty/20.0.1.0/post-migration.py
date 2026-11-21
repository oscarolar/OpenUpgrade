from openupgradelib import openupgrade

from odoo import SUPERUSER_ID
from odoo.tools import split_every


def loyalty_card_points(env):
    """
    loyalty.card#points is not stored anymore but computed from the history
    lines of the card. Add a history line for the difference between the
    former stored balance and the sum of the history lines, so that every card
    keeps its balance
    """
    if not openupgrade.column_exists(env.cr, "loyalty_card", "points"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO loyalty_history (
            card_id, description, issued, used, points_changed_date,
            create_uid, create_date, write_uid, write_date
        )
        SELECT
            balance.card_id,
            'Balance adjustment (migration to 20.0)',
            GREATEST(balance.difference, 0),
            GREATEST(-balance.difference, 0),
            NOW() AT TIME ZONE 'UTC',
            %(uid)s, NOW() AT TIME ZONE 'UTC',
            %(uid)s, NOW() AT TIME ZONE 'UTC'
        FROM (
            SELECT
                loyalty_card.id AS card_id,
                COALESCE(loyalty_card.points, 0) - COALESCE(history.points, 0)
                AS difference
            FROM
                loyalty_card
            LEFT JOIN (
                SELECT
                    card_id,
                    SUM(COALESCE(issued, 0) - COALESCE(used, 0)) AS points
                FROM
                    loyalty_history
                GROUP BY
                    card_id
            ) history
            ON
                history.card_id=loyalty_card.id
        ) balance
        WHERE
            ABS(balance.difference) >= 0.005
        """,
        {"uid": SUPERUSER_ID},
    )


def loyalty_history_settle_debt(env):
    """
    Consumption lines of loyalty programs must be linked to the awarding lines
    they draw from, unlinked ones are debts. Link the existing lines with the
    standard method, as otherwise they would be drawn later from new awards
    that can expire
    """
    env.cr.execute(
        """
        SELECT DISTINCT
            loyalty_history.card_id
        FROM
            loyalty_history
        JOIN
            loyalty_card
        ON
            loyalty_card.id=loyalty_history.card_id
        JOIN
            loyalty_program
        ON
            loyalty_program.id=loyalty_card.program_id
        WHERE
            loyalty_program.program_type='loyalty'
        AND
            loyalty_history.used > 0
        AND
            loyalty_history.linked_loyalty_history_id IS NULL
        ORDER BY
            loyalty_history.card_id
        """
    )
    card_ids = [card_id for (card_id,) in env.cr.fetchall()]
    LoyaltyCard = env["loyalty.card"]
    LoyaltyHistory = env["loyalty.history"]
    for chunk in split_every(1000, card_ids):
        LoyaltyHistory._settle_outstanding_debt(LoyaltyCard.browse(chunk))
        env.flush_all()
        env.invalidate_all()


@openupgrade.migrate()
def migrate(env, version):
    loyalty_card_points(env)
    loyalty_history_settle_debt(env)

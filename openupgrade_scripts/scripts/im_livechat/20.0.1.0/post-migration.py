# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_rating_case = """
    CASE
        WHEN {value} >= 4 THEN '5'
        WHEN {value} >= 3 THEN '3'
        WHEN {value} >= 1 THEN '1'
    END
"""


def discuss_channel_livechat_rating(env):
    """
    Live chat conversations don't use rating.mixin anymore, keep their last rating
    in livechat_rating
    """
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE discuss_channel
        SET livechat_rating={_rating_case.format(value="rating_last_value")}
        WHERE channel_type='livechat' AND rating_last_value >= 1
        """,
    )


def im_livechat_channel_member_history_rating(env):
    """
    Fill the rating of agents and bots from the rating.rating record they were
    linked to
    """
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE im_livechat_channel_member_history history
        SET rating={_rating_case.format(value="rating_rating.rating")}
        FROM rating_rating
        WHERE history.rating_id=rating_rating.id AND rating_rating.rating >= 1
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "im_livechat", "20.0.1.0/noupdate_changes.xml")
    discuss_channel_livechat_rating(env)
    im_livechat_channel_member_history_rating(env)

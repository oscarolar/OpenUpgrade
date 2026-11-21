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


def im_livechat_channel_member_history_operator(env):
    """
    Conversations from before v19 have no member history, and their agent was only
    in livechat_operator_id, which is gone. Create the history of the agent (or
    bot) and link it to the conversation
    """
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO im_livechat_channel_member_history (
            channel_id, partner_id, member_id, livechat_member_type,
            chatbot_script_id, create_uid, write_uid, create_date, write_date
        )
        SELECT
            discuss_channel.id,
            discuss_channel.livechat_operator_id,
            (
                SELECT discuss_channel_member.id
                FROM discuss_channel_member
                WHERE discuss_channel_member.channel_id=discuss_channel.id
                AND discuss_channel_member.partner_id=
                    discuss_channel.livechat_operator_id
                AND NOT EXISTS (
                    SELECT 1
                    FROM im_livechat_channel_member_history history
                    WHERE history.member_id=discuss_channel_member.id
                )
                ORDER BY discuss_channel_member.id
                LIMIT 1
            ),
            CASE WHEN chatbot.id IS NULL THEN 'agent' ELSE 'bot' END,
            chatbot.id,
            discuss_channel.create_uid,
            discuss_channel.create_uid,
            discuss_channel.create_date,
            discuss_channel.create_date
        FROM discuss_channel
        LEFT JOIN LATERAL (
            SELECT chatbot_script.id
            FROM chatbot_script
            WHERE chatbot_script.operator_partner_id=
                discuss_channel.livechat_operator_id
            ORDER BY chatbot_script.id
            LIMIT 1
        ) chatbot ON TRUE
        WHERE discuss_channel.channel_type='livechat'
        AND discuss_channel.livechat_operator_id IS NOT NULL
        AND NOT EXISTS (
            SELECT 1
            FROM im_livechat_channel_member_history history
            WHERE history.channel_id=discuss_channel.id
            AND (
                history.livechat_member_type IN ('agent', 'bot')
                OR history.partner_id=discuss_channel.livechat_operator_id
            )
        )
        """,
    )
    for member_type in ("agent", "bot"):
        table = f"im_livechat_channel_member_history_discuss_channel_{member_type}_rel"
        openupgrade.logged_query(
            env.cr,
            f"""
            INSERT INTO {table} (discuss_channel_id, res_partner_id)
            SELECT DISTINCT channel_id, partner_id
            FROM im_livechat_channel_member_history
            WHERE livechat_member_type='{member_type}'
            AND channel_id IS NOT NULL AND partner_id IS NOT NULL
            ON CONFLICT DO NOTHING
            """,
        )


def im_livechat_channel_member_history_rating(env):
    """
    Fill the rating of agents and bots from the rating.rating record they were
    linked to, and from the rating of the conversation for the ones without it
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
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE im_livechat_channel_member_history history
        SET rating=discuss_channel.livechat_rating
        FROM discuss_channel
        WHERE history.channel_id=discuss_channel.id
        AND history.rating IS NULL
        AND history.rating_id IS NULL
        AND discuss_channel.livechat_rating IS NOT NULL
        AND (
            history.livechat_member_type='agent'
            OR (
                history.livechat_member_type='bot'
                AND NOT EXISTS (
                    SELECT 1
                    FROM im_livechat_channel_member_history agent_history
                    WHERE agent_history.channel_id=history.channel_id
                    AND agent_history.livechat_member_type='agent'
                )
            )
        )
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "im_livechat", "20.0.1.0/noupdate_changes.xml")
    discuss_channel_livechat_rating(env)
    im_livechat_channel_member_history_operator(env)
    im_livechat_channel_member_history_rating(env)

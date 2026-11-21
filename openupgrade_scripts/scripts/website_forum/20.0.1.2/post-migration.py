# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def forum_post_comment(env):
    """
    Posts don't inherit mail.thread anymore, their comments were mail.message
    records and are forum.post.comment records now
    """
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO forum_post_comment
            (post_id, body, create_uid, write_uid, create_date, write_date)
        SELECT
            forum_post.id,
            mail_message.body,
            COALESCE(author_user.id, mail_message.create_uid),
            COALESCE(author_user.id, mail_message.write_uid),
            COALESCE(mail_message.date, mail_message.create_date),
            mail_message.write_date
        FROM mail_message
        JOIN forum_post ON mail_message.res_id=forum_post.id
        LEFT JOIN LATERAL (
            SELECT id
            FROM res_users
            WHERE res_users.partner_id=mail_message.author_id
            ORDER BY active DESC, id
            LIMIT 1
        ) author_user ON TRUE
        WHERE mail_message.model='forum.post'
        AND mail_message.message_type='comment'
        AND COALESCE(mail_message.body, '') <> ''
        ORDER BY mail_message.id
        """,
    )


def forum_followers(env):
    """
    Followers of posts and tags were mail.followers records and are plain
    many2many relations to partners now
    """
    for model in ("forum.post", "forum.tag"):
        table = model.replace(".", "_")
        openupgrade.logged_query(
            env.cr,
            f"""
            INSERT INTO {table}_follower_rel ({table}_id, res_partner_id)
            SELECT DISTINCT mail_followers.res_id, mail_followers.partner_id
            FROM mail_followers
            JOIN {table} ON mail_followers.res_id={table}.id
            WHERE mail_followers.res_model=%s
            AND mail_followers.partner_id IS NOT NULL
            ON CONFLICT DO NOTHING
            """,
            (model,),
        )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "website_forum", "20.0.1.2/noupdate_changes.xml")
    forum_post_comment(env)
    forum_followers(env)

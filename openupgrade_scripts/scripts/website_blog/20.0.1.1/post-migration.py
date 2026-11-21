# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def blog_post_scheduled(env):
    """
    Posts published with a publishing date in the future were hidden until that
    date: unpublish and schedule them with blog.post#publish_on
    """
    count = openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            blog_post
        SET
            publish_on=post_date,
            is_published=FALSE
        WHERE
            is_published
        AND
            post_date > (now() AT TIME ZONE 'UTC')
        """,
    )
    if count:
        env["blog.post"].invalidate_model(["publish_on", "is_published"])
        env["blog.post"]._manage_next_scheduled_action()


def blog_post_published_date(env):
    """
    Fill blog.post#published_date from blog.post#post_date for published posts
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            blog_post
        SET
            published_date=COALESCE(post_date, create_date)
        WHERE
            is_published
        AND
            published_date IS NULL
        """,
    )


def cover_properties_webp(env):
    """
    Cover images shipped with the module were converted from jpg to webp
    """
    path = "/website_blog/static/src/img/(cover|blog)_[0-9]+"
    for table in ("blog_blog", "blog_post"):
        openupgrade.logged_query(
            env.cr,
            rf"""
            UPDATE
                {table}
            SET
                cover_properties=regexp_replace(
                    cover_properties, '({path})\.jpe?g', '\1.webp', 'g'
                )
            WHERE
                cover_properties ~ '{path}\.jpe?g'
            """,
        )


def group_website_blog_manager(env):
    """
    Add the users who could edit blogs in v19 to the new blog manager group
    """
    designer = env.ref("website.group_website_designer")
    manager = env.ref("website_blog.group_website_blog_manager")
    manager.write({"user_ids": [(4, user_id) for user_id in designer.all_user_ids.ids]})


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "website_blog", "20.0.1.1/noupdate_changes.xml")
    blog_post_scheduled(env)
    blog_post_published_date(env)
    cover_properties_webp(env)
    group_website_blog_manager(env)

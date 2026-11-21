# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from markupsafe import escape
from openupgradelib import openupgrade
from psycopg2.extras import Json

_social_media = [
    "discord",
    "facebook",
    "github",
    "instagram",
    "linkedin",
    "tiktok",
    "twitter",
    "youtube",
]

_social_link_re = re.compile(r"""(?<=["'])/website/social/(\w+)(?=["'])""")


def website_page_date_publish(env):
    """
    website.page#date_publish hid published pages until that date. Pages whose date
    has passed keep it as published_date, the others are scheduled with publish_on
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE website_page
        SET published_date=date_publish
        WHERE is_published AND date_publish <= (now() AT TIME ZONE 'UTC')
        """,
    )
    scheduled = openupgrade.logged_query(
        env.cr,
        """
        UPDATE website_page
        SET publish_on=date_publish, is_published=False
        WHERE is_published AND date_publish > (now() AT TIME ZONE 'UTC')
        """,
    )
    if scheduled:
        env["website.page"].invalidate_model(["publish_on", "is_published"])
        env["website.published.mixin"]._manage_next_scheduled_action()


def website_cookie_policy_id(env):
    """
    Link websites showing the cookies bar to their existing cookie policy page
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE website
        SET cookie_policy_id=website_page.id
        FROM website_page
        WHERE website_page.website_id=website.id
        AND website_page.url->>'en_US'='/cookie-policy'
        AND website.cookies_bar
        AND website.cookie_policy_id IS NULL
        """,
    )


def res_company_social_media(env):
    """
    The social media accounts of a website are gone, only the ones of its company
    remain. Fill empty company accounts from the first website of the company
    """
    for social in _social_media:
        openupgrade.logged_query(
            env.cr,
            f"""
            UPDATE res_company
            SET social_{social}=first_website.social_{social}
            FROM (
                SELECT DISTINCT ON (company_id) company_id, social_{social}
                FROM website
                WHERE COALESCE(social_{social}, '') <> ''
                ORDER BY company_id, sequence, id
            ) first_website
            WHERE first_website.company_id=res_company.id
            AND COALESCE(res_company.social_{social}, '') = ''
            """,
        )


def website_social_links(env):
    """
    The controller /website/social/<name> redirecting to the account of the website
    is gone, write the account url of the website in the links of customized views
    and mega menus
    """
    columns = ", ".join(f"social_{social}" for social in _social_media)
    env.cr.execute(f"SELECT id, {columns} FROM website ORDER BY sequence, id")
    websites = {row["id"]: row for row in env.cr.dictfetchall()}
    if not websites:
        return
    default_website = next(iter(websites.values()))

    for table, column in (
        ("ir_ui_view", "arch_db"),
        ("website_menu", "mega_menu_content"),
    ):
        env.cr.execute(
            f"""
            SELECT id, website_id, {column}
            FROM {table}
            WHERE {column}::text LIKE '%/website/social/%'
            """
        )
        for record_id, website_id, translations in env.cr.fetchall():
            website = websites.get(website_id, default_website)

            def replace(match, website=website):
                url = website.get(f"social_{match.group(1)}")
                return str(escape(url)) if url else match.group(0)

            new_translations = {
                lang: _social_link_re.sub(replace, value) if value else value
                for lang, value in translations.items()
            }
            if new_translations != translations:
                env.cr.execute(
                    f"UPDATE {table} SET {column}=%s WHERE id=%s",
                    (Json(new_translations), record_id),
                )
    env.invalidate_all()


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "website", "20.0.1.0/noupdate_changes.xml")
    website_page_date_publish(env)
    website_cookie_policy_id(env)
    res_company_social_media(env)
    website_social_links(env)

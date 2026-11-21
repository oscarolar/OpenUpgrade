# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_columns = {
    "website_menu": [
        ("url", "manual_url"),
    ],
}


def ir_ui_view_visibility(env):
    """
    The empty selection key for public views is now 'public' and the field is required
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_ui_view
        SET visibility='public'
        WHERE visibility IS NULL OR visibility=''
        """,
    )


def website_menu_manual_url(env):
    """
    website.menu#url is computed from the page now, the user defined value lives in
    manual_url and is only used for menus without page
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE website_menu
        SET manual_url=''
        WHERE page_id IS NOT NULL
        """,
    )


def website_page_name(env):
    """
    website.page#name is stored and translatable now, fill it from the view
    """
    openupgrade.logged_query(
        env.cr, "ALTER TABLE website_page ADD COLUMN IF NOT EXISTS name jsonb"
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE website_page
        SET name=jsonb_build_object('en_US', ir_ui_view.name)
        FROM ir_ui_view
        WHERE website_page.view_id=ir_ui_view.id
        AND ir_ui_view.name IS NOT NULL
        """,
    )


def website_rewrite_required(env):
    """
    Fill website.rewrite fields that are required now, redirect_type with the v19
    default
    """
    openupgrade.logged_query(
        env.cr,
        "UPDATE website_rewrite SET redirect_type='302' WHERE redirect_type IS NULL",
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE website_rewrite
        SET url_from=COALESCE(website_route.path, '')
        FROM website_rewrite website_rewrite2
        LEFT JOIN website_route ON website_rewrite2.route_id=website_route.id
        WHERE website_rewrite.id=website_rewrite2.id
        AND website_rewrite.url_from IS NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_columns(env.cr, _renamed_columns)
    ir_ui_view_visibility(env)
    website_menu_manual_url(env)
    website_page_name(env)
    website_rewrite_required(env)

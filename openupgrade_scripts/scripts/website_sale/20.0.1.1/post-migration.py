# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def product_stock_notification(env):
    """
    Create product.stock.notification records from
    product.product#stock_notification_partner_ids of website_sale_stock, for the
    website of the product, of the partner or the default one
    """
    if not openupgrade.table_exists(env.cr, "stock_notification_product_partner_rel"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO product_stock_notification_rel (
            product_id, partner_id, website_id,
            create_uid, create_date, write_uid, write_date
        )
        SELECT
            rel.product_product_id,
            rel.res_partner_id,
            COALESCE(
                product_template.website_id, res_partner.website_id, default_website.id
            ),
            1, NOW() AT TIME ZONE 'UTC', 1, NOW() AT TIME ZONE 'UTC'
        FROM
            stock_notification_product_partner_rel rel
        JOIN
            product_product ON rel.product_product_id=product_product.id
        JOIN
            product_template
            ON product_product.product_tmpl_id=product_template.id
        JOIN
            res_partner ON rel.res_partner_id=res_partner.id
        LEFT JOIN
            (SELECT id FROM website ORDER BY sequence, id LIMIT 1) default_website
            ON True
        WHERE
            COALESCE(
                product_template.website_id, res_partner.website_id, default_website.id
            ) IS NOT NULL
        ON CONFLICT DO NOTHING
        """,
    )


def website_category_options(env):
    """
    The display options of product.public.category moved to website: the title and
    the alignment are enabled when all the categories of the website had them, the
    description when any of them had it (it was shown by default)
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE website
        SET
            show_category_title=options.show_category_title,
            show_category_description=options.show_category_description,
            align_category_content=options.align_category_content
        FROM (
            SELECT
                website.id AS website_id,
                bool_and(COALESCE(category.show_category_title, False))
                    AS show_category_title,
                bool_or(COALESCE(category.show_category_description, True))
                    AS show_category_description,
                bool_and(COALESCE(category.align_category_content, False))
                    AS align_category_content
            FROM
                website
            JOIN
                product_public_category category
                ON category.website_id IS NULL OR category.website_id=website.id
            GROUP BY website.id
        ) options
        WHERE options.website_id=website.id
        """,
    )


def website_checkout_steps(env):
    """
    Create the new checkout steps for each website
    """
    WebsiteCheckoutStep = env["website.checkout.step"].with_context(active_test=False)
    generic_steps = WebsiteCheckoutStep.search(
        [
            ("website_id", "=", False),
            ("step_href", "in", ("/shop/address", "/shop/payment/transaction")),
        ]
    )
    for website in env["website"].with_context(active_test=False).search([]):
        existing_hrefs = WebsiteCheckoutStep.search(
            [("website_id", "=", website.id)]
        ).mapped("step_href")
        for step in generic_steps:
            if step.step_href not in existing_hrefs:
                step.copy({"website_id": website.id, "is_published": True})


def website_rating_email_template_id(env):
    """
    Set the default of website#rating_email_template_id, the template didn't exist
    yet when the column was created
    """
    template = env.ref(
        "website_sale.mail_template_sale_order_rating", raise_if_not_found=False
    )
    if not template:
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE website
        SET rating_email_template_id=%s
        WHERE rating_email_template_id IS NULL
        """,
        (template.id,),
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "website_sale", "20.0.1.1/noupdate_changes.xml")
    openupgrade.delete_record_translations(
        env.cr,
        "website_sale",
        ["mail_template_sale_cart_recovery"],
        ["body_html", "subject"],
    )
    product_stock_notification(env)
    website_category_options(env)
    website_checkout_steps(env)
    website_rating_email_template_id(env)
    env["website"]._toggle_abandoned_cart_email_cron()

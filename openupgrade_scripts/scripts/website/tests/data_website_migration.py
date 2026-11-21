env = locals().get("env")
website = env.ref("website.default_website")
website.social_facebook = "https://www.facebook.com/openupgrade?a=1&b=2"
env["website.menu"].create(
    {
        "name": "OpenUpgrade v20 test menu",
        "url": "/openupgrade-v20-test",
        "website_id": website.id,
        "parent_id": website.menu_id.id,
    }
)
view = env["ir.ui.view"].create(
    {
        "name": "OpenUpgrade v20 test page",
        "type": "qweb",
        "key": "website.openupgrade_v20_test_page",
        "website_id": website.id,
        "arch": """<t t-call="website.layout">
            <div id="wrap"><a href="/website/social/facebook">Facebook</a></div>
        </t>""",
    }
)
env["website.page"].create(
    {
        "url": "/openupgrade-v20-test-page",
        "view_id": view.id,
        "website_id": website.id,
        "is_published": True,
        "date_publish": "2099-01-01 00:00:00",
    }
)
env.cr.commit()

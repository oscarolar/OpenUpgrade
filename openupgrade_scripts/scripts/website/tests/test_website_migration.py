from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestWebsiteMigration(TransactionCase):
    def test_menu_url(self):
        """
        Test that the url of menus without page is kept
        """
        menu = self.env["website.menu"].search(
            [("name", "=", "OpenUpgrade v20 test menu")]
        )
        self.assertEqual(menu.manual_url, "/openupgrade-v20-test")
        self.assertEqual(menu.url, "/openupgrade-v20-test")

    def test_page(self):
        """
        Test that pages get the name of their view and that pages published in the
        future are scheduled
        """
        page = self.env["website.page"].search(
            [("url", "=", "/openupgrade-v20-test-page")]
        )
        self.assertEqual(page.name, "OpenUpgrade v20 test page")
        self.assertFalse(page.is_published)
        self.assertEqual(str(page.publish_on), "2099-01-01 00:00:00")

    def test_social_links(self):
        """
        Test that links to the removed social media controller point to the account
        """
        view = self.env["ir.ui.view"].search(
            [("key", "=", "website.openupgrade_v20_test_page")]
        )
        self.assertNotIn("/website/social/facebook", view.arch_db)
        self.assertIn(
            'href="https://www.facebook.com/openupgrade?a=1&amp;b=2"', view.arch_db
        )

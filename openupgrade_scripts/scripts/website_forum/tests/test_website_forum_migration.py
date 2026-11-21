from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestWebsiteForumMigration(TransactionCase):
    def test_comments_and_followers(self):
        """
        Test that comments and followers of posts are kept
        """
        post = self.env["forum.post"].search(
            [("name", "=", "OpenUpgrade v20 test question")]
        )
        self.assertEqual(len(post.comment_ids), 1)
        self.assertIn("OpenUpgrade v20 test comment", post.comment_ids.body)
        self.assertEqual(post.comment_ids.create_uid, self.env.ref("base.user_root"))
        self.assertIn(
            "OpenUpgrade v20 forum follower", post.sudo().follower_ids.mapped("name")
        )

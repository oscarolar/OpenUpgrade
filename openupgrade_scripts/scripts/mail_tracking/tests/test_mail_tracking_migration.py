from odoo.tests import TransactionCase, tagged

from odoo.addons.openupgrade_framework import openupgrade_test


@tagged("-at_install", "post_install")
@openupgrade_test
class TestMailTrackingMigration(TransactionCase):
    def test_tracking(self):
        """
        Test that tracking values are kept in mail_tracking and rendered in the body
        """
        message = self.env["mail.message"].search(
            [("subject", "=", "OpenUpgrade v20 tracking")]
        )
        self.assertEqual(message.message_type, "tracking")
        self.assertEqual(len(message.tracking_value_ids), 2)
        self.assertEqual(
            message.body,
            "<div>No → <b>Yes</b> <i>(Active)</i><br>"
            "old@example.com → <b>&lt;new&gt;@example.com</b> <i>(Email)</i></div>",
        )
        self.assertEqual(
            self.env.ref("mail_tracking.model_mail_tracking_value").model,
            "mail.tracking.value",
        )
        self.assertFalse(
            self.env.ref("mail.model_mail_tracking_value", raise_if_not_found=False)
        )

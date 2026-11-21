from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestMailMigration(TransactionCase):
    def test_channel_owner(self):
        """
        Test that channels are assigned owners
        """
        test_channel = self.env["discuss.channel"].search(
            [("name", "=", "OpenUpgrade v20 test channel")]
        )
        self.assertEqual(
            test_channel.channel_member_ids.filtered(
                lambda x: x.partner_id.user_ids.login == "test_user_v19"
            ).channel_role,
            "owner",
        )

    def test_mail_post_actions(self):
        """
        Test that server actions that logged a note or sent an email without posting
        still do that instead of posting a comment for the followers
        """
        partner = self.env["res.partner"].create({"name": "OU20 partner"})
        follower = self.env["res.partner"].create(
            {"name": "OU20 follower", "email": "follower@example.com"}
        )
        partner.message_subscribe(follower.ids)
        Action = self.env["ir.actions.server"]
        note_action = Action.search([("name", "=", "OU20 note")])
        if not note_action:
            self.skipTest("data_mail_migration.py was not loaded with the actions")
        self.assertEqual(note_action.state, "code")
        note_action.with_context(
            active_model="res.partner", active_ids=partner.ids, active_id=partner.id
        ).run()
        message = partner.message_ids[0]
        self.assertIn("OU20 body", message.body)
        self.assertEqual(message.subtype_id, self.env.ref("mail.mt_note"))
        self.assertNotIn(follower, message.notified_partner_ids)
        mails = self.env["mail.mail"].search([])
        email_action = Action.search([("name", "=", "OU20 email")])
        self.assertEqual(email_action.state, "code")
        email_action.with_context(
            active_model="res.partner", active_ids=partner.ids, active_id=partner.id
        ).run()
        mail = self.env["mail.mail"].search([]) - mails
        self.assertEqual(mail.subject, "OU20 subject")
        self.assertNotIn(follower, mail.recipient_ids)
        self.assertNotIn(follower, mail.mail_message_id.notified_partner_ids)

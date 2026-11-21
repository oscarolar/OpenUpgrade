from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestCrmMigration(TransactionCase):
    def test_duration_tracking(self):
        """
        Test that the time spent in previous stages is kept
        """
        lead = self.env["crm.lead"].search([("name", "=", "OpenUpgrade v20 test lead")])
        self.assertTrue(lead)
        stages = self.env["crm.stage"].search([], limit=3)
        duration = lead.duration_tracking
        self.assertEqual(duration["s"], lead.stage_id.id)
        self.assertTrue(duration["d"])
        self.assertGreaterEqual(duration[str(stages[1].id)], 59)
        self.assertLessEqual(duration[str(stages[1].id)], 61)

    def test_assignment_optout(self):
        """
        Test that members who paused assignment are out of rotation
        """
        self.env.cr.execute(
            "SELECT id FROM crm_team_member WHERE assignment_optout LIMIT 1"
        )
        for (member_id,) in self.env.cr.fetchall():
            member = self.env["crm.team.member"].browse(member_id)
            self.assertEqual(member.assignment_rules, "opt-out")

from openupgradelib import openupgrade

from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestProjectMigration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].search(
            [("name", "=", "OpenUpgrade v20 shared project")]
        )
        cls.task = cls.env["project.task"].search(
            [("name", "=", "OpenUpgrade v20 followed task")]
        )

    def _partner(self, name):
        return self.env["res.users"].search([("login", "=", f"ou20_project_{name}")])[
            "partner_id"
        ]

    def test_collaborators(self):
        """
        Test that nobody gains access to all the tasks of the project: only the
        collaborator without limited access stays as collaborator
        """
        self.assertTrue(self.project)
        collaborator = self.project.collaborator_ids
        self.assertEqual(collaborator.partner_id, self._partner("collaborator"))
        self.assertEqual(collaborator.access_mode, "advanced_edit")
        self.env.cr.execute(
            "SELECT partner_id FROM "
            + openupgrade.get_legacy_name("project_collaborator_limited")
            + " WHERE project_id = %s",
            (self.project.id,),
        )
        self.assertEqual(
            [row[0] for row in self.env.cr.fetchall()], self._partner("limited").ids
        )

    def test_followed_tasks(self):
        """
        Test that the followers keep following their tasks
        """
        self.assertIn(self._partner("limited"), self.task.message_partner_ids)
        self.assertIn(self._partner("follower"), self.task.message_partner_ids)
        self.assertIn(self._partner("follower"), self.project.message_partner_ids)

    def test_duration_tracking(self):
        """
        Test that the stored duration tracking has the previous and current stages
        """
        tracking = self.task.duration_tracking
        self.assertEqual(tracking["s"], self.task.stage_id.id)
        previous_stage = self.env["project.task.type"].search(
            [("name", "=", "OpenUpgrade v20 stage 1")]
        )
        self.assertIn(str(previous_stage.id), tracking)

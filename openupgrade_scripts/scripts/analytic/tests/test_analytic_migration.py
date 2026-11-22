from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestAnalyticMigration(TransactionCase):
    def test_project_plan_name(self):
        """
        A project plan renamed by the user keeps its name
        """
        self.assertEqual(
            self.env.ref("analytic.analytic_plan_projects").name, "OU Departments"
        )

from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestHrFleetMigration(TransactionCase):
    def test_offboarding_fleet(self):
        """
        Test that the unmodified fleet template of the offboarding plan is deleted
        and the other fleet manager templates are asked at launch
        """
        self.assertFalse(
            self.env.ref("hr_fleet.offboarding_fleet", raise_if_not_found=False)
        )
        template = self.env["mail.activity.plan.template"].search(
            [("summary", "=", "OpenUpgrade v20 fleet template")]
        )
        self.assertEqual(template.responsible_type, "on_demand")

from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestMassMailingCrmMigration(TransactionCase):
    def test_lead_count(self):
        """
        Test that the leads of a mailing are still counted
        """
        mailing = self.env["mailing.mailing"].search(
            [("subject", "=", "OpenUpgrade v20 test mailing")]
        )
        self.assertEqual(mailing.crm_lead_count, 1)

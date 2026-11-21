from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestLunchMigration(TransactionCase):
    def test_24_hours(self):
        """
        Test that pm times get 12 hours and the moment is reset
        """
        supplier = self.env["lunch.supplier"].search(
            [("partner_id.name", "=", "OpenUpgrade v20 lunch vendor")]
        )
        self.assertEqual(supplier.automatic_email_time, 15.5)
        Alert = self.env["lunch.alert"]
        alert = Alert.search([("name", "=", "OpenUpgrade v20 alert")])
        self.assertEqual(alert.notification_time, 13.0)
        morning = Alert.search([("name", "=", "OpenUpgrade v20 morning alert")])
        self.assertEqual(morning.notification_time, 9.0)
        self.env.cr.execute(
            "SELECT moment FROM lunch_supplier WHERE id = %s", (supplier.id,)
        )
        self.assertEqual(self.env.cr.fetchone()[0], "am")
        self.env.cr.execute(
            "SELECT notification_moment FROM lunch_alert WHERE id = %s", (alert.id,)
        )
        self.assertEqual(self.env.cr.fetchone()[0], "am")

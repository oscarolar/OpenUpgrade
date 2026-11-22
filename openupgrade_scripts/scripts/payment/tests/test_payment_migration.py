from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestPaymentMigration(TransactionCase):
    def test_provider_sequence(self):
        """
        The new default order only applies to the providers that kept the old
        default
        """
        self.assertEqual(self.env.ref("payment.payment_provider_transfer").sequence, 7)
        self.assertEqual(self.env.ref("payment.payment_provider_demo").sequence, 10)

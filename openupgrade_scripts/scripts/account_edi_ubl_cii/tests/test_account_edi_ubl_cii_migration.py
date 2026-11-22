from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestAccountEdiUblCiiMigration(TransactionCase):
    def test_routing(self):
        """
        The Peppol address of the partner is kept as its routing address
        """
        partner = self.env["res.partner"].search(
            [("name", "=", "OU Peppol GLN partner")]
        )
        self.assertEqual(partner.routing_scheme, "0088")
        self.assertEqual(partner.routing_endpoint, "5401234567898")
        self.assertEqual(partner.routing_identifier, "0088:5401234567898")

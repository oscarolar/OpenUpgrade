from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestL10nCoMigration(TransactionCase):
    def test_identification_type(self):
        """
        The citizen id becomes an additional identifier and the DIAN code
        follows it
        """
        partner = self.env["res.partner"].search([("name", "=", "OU CO CC partner")])
        self.assertFalse(partner.vat)
        self.assertEqual(partner.additional_identifiers.get("CO_CC"), "1020304050")
        self.assertEqual(partner.l10n_co_dian_id_code, "13")

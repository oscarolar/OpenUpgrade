from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestL10nPeMigration(TransactionCase):
    def test_identification_type(self):
        """
        The DNI becomes an additional identifier and the SUNAT code follows it
        """
        partner = self.env["res.partner"].search([("name", "=", "OU PE DNI partner")])
        self.assertFalse(partner.vat)
        self.assertEqual(partner.additional_identifiers.get("PE_DNI"), "40000004")
        self.assertEqual(partner.l10n_pe_sunat_id_code, "1")

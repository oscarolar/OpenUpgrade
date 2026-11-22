from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestL10nArMigration(TransactionCase):
    def _partner(self, name):
        return self.env["res.partner"].search([("name", "=", name)])

    def test_identification_type(self):
        """
        Only the CUIT stays in vat, the other documents become additional
        identifiers and the AFIP code is computed from them
        """
        dni = self._partner("OU AR DNI partner")
        self.assertFalse(dni.vat)
        self.assertEqual(dni.additional_identifiers.get("AR_DNI"), "26254396")
        self.assertEqual(dni.l10n_ar_afip_code, "96")
        self.assertEqual(dni.l10n_ar_afip_id_value, "26254396")
        cuit = self._partner("OU AR CUIT partner")
        self.assertEqual(cuit.vat, "30714295698")
        self.assertEqual(cuit.l10n_ar_afip_code, "80")
        ci = self._partner("OU AR CI partner")
        self.assertFalse(ci.vat)
        self.assertEqual(ci.additional_identifiers.get("AR_CI"), "12345678")
        self.assertEqual(ci.l10n_ar_afip_code, "1")

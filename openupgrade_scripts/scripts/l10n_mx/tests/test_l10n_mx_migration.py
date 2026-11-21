from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestL10nMxMigration(TransactionCase):
    def test_bank_abm_code(self):
        """
        The ABM code of the bank becomes the clearing number of the account
        """
        ResPartnerBank = self.env["res.partner.bank"]
        account = ResPartnerBank.search([("account_number", "=", "OU0001234567")])
        self.assertEqual(account.clearing_number, "002")
        self.assertEqual(
            account.clearing_label_id, self.env.ref("base.clearing_label_mx")
        )
        self.assertEqual(account.bank_name, "BANAMEX")
        self.assertIn("CLABE: 002010077777777771", account.note)
        clabe_account = ResPartnerBank.search(
            [("account_number", "=", "012180001234567895")]
        )
        self.assertEqual(clabe_account.clearing_number, "012")
        self.assertFalse(clabe_account.note)

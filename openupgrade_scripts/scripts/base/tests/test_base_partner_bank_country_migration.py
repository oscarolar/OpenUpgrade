import importlib.util
import os

from odoo.tests import TransactionCase, tagged

from odoo.addons.openupgrade_framework import openupgrade_test


def _load_script(version, script):
    path = os.path.join(os.path.dirname(__file__), os.pardir, version, script)
    spec = importlib.util.spec_from_file_location(f"ou20_base_{version}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("-at_install", "post_install")
@openupgrade_test
class TestBasePartnerBankCountryMigration(TransactionCase):
    def setUp(self):
        super().setUp()
        self.accounts = self.env["res.partner.bank"].search(
            [("account_number", "like", "OU20-BANK-%")], order="account_number"
        )
        if len(self.accounts) != 5:
            self.skipTest("data_base_partner_bank_country.py was not loaded")
        self.script = _load_script("20.0.1.3", "post-migration.py")

    def _state(self):
        self.env.invalidate_all()
        return {
            account.account_number: (
                account.country_id.code,
                account.clearing_label_id.country_id.code,
            )
            for account in self.accounts
        }

    def test_country_from_partner_or_usage(self):
        main = self.env.ref("base.main_company").country_id.code
        self.assertEqual(
            self._state(),
            {
                "OU20-BANK-1": ("CA", "CA"),
                "OU20-BANK-2": ("CA", "CA"),
                "OU20-BANK-3": ("JP", "JP"),
                "OU20-BANK-4": (main, main),
                "OU20-BANK-5": ("CA", "CA"),
            },
        )

    def test_clearing_number_of_the_country(self):
        account = self.accounts.filtered(
            lambda account: account.account_number == "OU20-BANK-2"
        )
        account.clearing_number = "0123-45678"
        self.assertEqual(account._get_clearing_number("CA"), "0123-45678")
        account = self.accounts.filtered(
            lambda account: account.account_number == "OU20-BANK-3"
        )
        account.clearing_number = "123"
        self.assertEqual(account._get_clearing_number("JP"), "123")

    def test_rerun_does_nothing(self):
        before = self._state()
        self.assertFalse(self.script.res_partner_bank_country(self.env))
        self.assertEqual(self._state(), before)

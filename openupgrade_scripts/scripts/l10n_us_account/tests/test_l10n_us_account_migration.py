import importlib.util
import os

from odoo.tests import TransactionCase, tagged

from odoo.addons.openupgrade_framework import openupgrade_test


def _load_script(version, script):
    path = os.path.join(os.path.dirname(__file__), os.pardir, version, script)
    spec = importlib.util.spec_from_file_location(f"ou20_l10n_us_{version}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("-at_install", "post_install")
@openupgrade_test
class TestL10nUsAccountMigration(TransactionCase):
    def setUp(self):
        super().setUp()
        self.accounts = self.env["res.partner.bank"].search(
            [("account_number", "like", "OU20-US-%")]
        )
        if len(self.accounts) != 4:
            self.skipTest("data_l10n_us_account_migration.py was not loaded")
        self.script = _load_script("20.0.1.0", "post-migration.py")

    def _state(self):
        self.env.invalidate_all()
        return {
            account.account_number: account.intermediary_bank_bic
            for account in self.accounts
        }

    def test_intermediary_bank_bic(self):
        self.assertEqual(
            self._state(),
            {
                "OU20-US-1": "OUINUS33XXX",
                "OU20-US-2": "OUINUS33XXX",
                "OU20-US-3": False,
                "OU20-US-4": False,
            },
        )
        account = self.accounts.filtered(lambda a: a.account_number == "OU20-US-1")
        self.assertEqual(account.bank_bic, "OUBKUS44XXX")

    def test_rerun_does_not_duplicate(self):
        before = self._state()
        self.script._res_partner_bank_intermediary_bank_bic(self.env)
        self.assertEqual(self._state(), before)

    def test_database_without_data(self):
        self.env.cr.execute(
            "UPDATE res_bank SET intermediary_bank_id = NULL; "
            "UPDATE res_partner_bank SET intermediary_bank_bic = NULL"
        )
        self.script._res_partner_bank_intermediary_bank_bic(self.env)
        self.env.invalidate_all()
        self.assertFalse(any(self._state().values()))

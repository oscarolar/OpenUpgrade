import importlib.util
import os

from odoo.tests import TransactionCase, tagged

from odoo.addons.openupgrade_framework import openupgrade_test


def _load_script(version, script):
    path = os.path.join(os.path.dirname(__file__), os.pardir, version, script)
    spec = importlib.util.spec_from_file_location(f"ou20_latam_check_{version}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("-at_install", "post_install")
@openupgrade_test
class TestL10nLatamCheckMigration(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env["res.company"].search([("name", "=", "OU20 AR CHK")])
        if not self.company:
            self.skipTest("data_l10n_latam_check_migration.py was not loaded")
        self.branch = self.env["res.company"].search(
            [("name", "=", "OU20 AR CHK branch")]
        )
        self.checks = (
            self.env["l10n_latam.check"]
            .sudo()
            .search([("payment_id.memo", "like", "OU20 CHK 0%")], order="name")
        )
        self.script = _load_script("20.0.1.0", "post-migration.py")

    def _state(self):
        self.env.invalidate_all()
        return [
            (check.name, check.bank_account_id.id, check.company_id.id)
            for check in self.checks
        ]

    def test_bank_account_at_the_bank_of_the_check(self):
        with_account, without_account = self.checks
        self.assertEqual(with_account.bank_account_id.account_number, "OU20-CHK-UNO")
        self.assertEqual(with_account.bank_account_id.bank_name, "OU20 Banco Uno")
        self.assertFalse(without_account.bank_account_id)

    def test_company_holding_the_check(self):
        transferred, kept = self.checks
        self.assertEqual(transferred.company_id, self.branch)
        self.assertEqual(transferred.payment_id.company_id, self.company)
        self.assertEqual(kept.company_id, self.company)

    def test_rerun_does_not_duplicate(self):
        before = self._state()
        self.script._l10n_latam_check_bank_account_id(self.env)
        self.script._l10n_latam_check_company_id(self.env)
        self.assertEqual(self._state(), before)

    def test_database_without_data(self):
        self.env.cr.execute("DELETE FROM l10n_latam_check_account_payment_rel")
        self.env.cr.execute("DELETE FROM l10n_latam_check")
        self.env.invalidate_all()
        self.script._l10n_latam_check_bank_account_id(self.env)
        self.script._l10n_latam_check_company_id(self.env)
        self.assertFalse(self.env["l10n_latam.check"].sudo().search([]))

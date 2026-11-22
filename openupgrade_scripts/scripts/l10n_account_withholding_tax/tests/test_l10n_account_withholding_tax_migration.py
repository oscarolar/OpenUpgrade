import importlib.util
import os

from odoo.tests import TransactionCase, tagged

from odoo.addons.openupgrade_framework import openupgrade_test


def _load_script(version, script):
    path = os.path.join(os.path.dirname(__file__), os.pardir, version, script)
    spec = importlib.util.spec_from_file_location(f"ou20_wht_{script}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("-at_install", "post_install")
@openupgrade_test
class TestL10nAccountWithholdingTaxMigration(TransactionCase):
    def setUp(self):
        super().setUp()
        self.payments = self.env["account.payment"].search(
            [("memo", "like", "OU20 WHT %")]
        )
        if len(self.payments) != 2:
            self.skipTest(
                "data_l10n_account_withholding_tax_migration.py was not loaded"
            )
        self.taxes = (
            self.env["account.tax"]
            .with_context(active_test=False)
            .search([("name", "like", "OU20 WHT %")])
        )
        self.post = _load_script("20.0.1.0", "post-migration.py")
        self.pre = _load_script("20.0.1.0", "pre-migration.py")

    def _state(self):
        self.env.invalidate_all()
        return (
            sorted(self.payments.mapped(lambda p: (p.memo, p.withhold))),
            sorted(self.taxes.mapped(lambda t: (t.name, t.is_withholding_tax))),
            self.env["account.tax"]
            .with_context(active_test=False)
            .search_count([("is_withholding_tax", "=", True)]),
        )

    def test_is_withholding_tax(self):
        self.assertEqual(
            {tax.name: tax.is_withholding_tax for tax in self.taxes},
            {"OU20 WHT on payment": True, "OU20 WHT regular": False},
        )
        self.env.cr.execute(
            """
            SELECT COUNT(*) FROM ir_model_fields
            WHERE model = 'account.tax' AND name = 'is_withholding_tax_on_payment'
            """
        )
        self.assertEqual(self.env.cr.fetchone()[0], 0)

    def test_withhold(self):
        self.assertEqual(
            {payment.memo: payment.withhold for payment in self.payments},
            {"OU20 WHT withheld": "withhold_pay", "OU20 WHT not withheld": "payment"},
        )

    def test_rerun_does_not_duplicate(self):
        before = self._state()
        self.pre._account_tax_is_withholding_tax(self.env)
        self.post._account_payment_withhold(self.env)
        self.assertEqual(self._state(), before)

    def test_database_without_data(self):
        self.env.cr.execute("UPDATE account_payment SET should_withhold_tax = NULL")
        self.env.cr.execute("UPDATE account_payment SET withhold = 'payment'")
        self.post._account_payment_withhold(self.env)
        self.env.invalidate_all()
        self.assertFalse(
            self.env["account.payment"].search([("withhold", "=", "withhold_pay")])
        )

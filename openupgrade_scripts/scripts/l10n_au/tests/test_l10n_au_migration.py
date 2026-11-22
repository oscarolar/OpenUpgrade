import importlib.util
import os

from odoo.tests import TransactionCase, tagged

from odoo.addons.openupgrade_framework import openupgrade_test


def _load_script(version, script):
    path = os.path.join(os.path.dirname(__file__), os.pardir, version, script)
    spec = importlib.util.spec_from_file_location(f"ou20_l10n_au_{version}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("-at_install", "post_install")
@openupgrade_test
class TestL10nAuMigration(TransactionCase):
    def setUp(self):
        super().setUp()
        self.accounts = self.env["res.partner.bank"].search(
            [("account_number", "like", "OU20-AU-%")]
        )
        if len(self.accounts) != 4:
            self.skipTest("data_l10n_au_migration.py was not loaded")
        self.script = _load_script("20.0.1.1", "post-migration.py")

    def _state(self):
        self.env.invalidate_all()
        return {
            account.account_number: account.clearing_number for account in self.accounts
        }

    def test_bsb_is_the_clearing_number(self):
        self.assertEqual(
            self._state(),
            {
                "OU20-AU-1": "123-456",
                "OU20-AU-2": "654321",
                "OU20-AU-3": False,
                "OU20-AU-4": "111 222",
            },
        )
        for account in self.accounts.filtered("clearing_number"):
            self.assertEqual(account.country_code, "AU", account.account_number)
            self.assertEqual(
                account._get_clearing_number("AU"),
                account.clearing_number,
                account.account_number,
            )
        self.accounts._check_clearing_number()

    def test_bas_tax_tags_stay_on_the_taxes(self):
        company = self.env["res.company"].search([("name", "=", "OU20 AU")])
        tags = self.env["account.account.tag"].search(
            [
                ("country_id.code", "=", "AU"),
                ("applicability", "=", "taxes"),
            ]
        )
        names = set(tags.with_context(lang="en_US").mapped("name"))
        for name in ("G1", "G2", "G3", "G4", "G7", "1C", "7A", "W2", "W4", "T7"):
            self.assertIn(name, names)
        sale = self.env.ref(f"account.{company.id}_au_tax_sale_10")
        self.assertIn(
            "G1",
            sale.invoice_repartition_line_ids.tag_ids.with_context(lang="en_US").mapped(
                "name"
            ),
        )
        self.assertFalse(
            self.env["ir.model.data"].search(
                [
                    ("module", "=", "l10n_au"),
                    ("model", "=", "account.report.expression"),
                    ("name", "=like", "account_tax_report_%"),
                ]
            )
        )

    def test_rerun_does_not_duplicate(self):
        before = self._state()
        self.script._res_partner_bank_clearing_number(self.env)
        self.script._account_report_expression_obsolete(self.env)
        self.assertEqual(self._state(), before)

    def test_database_without_data(self):
        self.env.cr.execute(
            "UPDATE res_partner_bank SET aba_bsb = NULL, clearing_number = NULL"
        )
        self.script._res_partner_bank_clearing_number(self.env)
        self.script._account_report_expression_obsolete(self.env)
        self.env.invalidate_all()
        self.assertFalse(any(self._state().values()))

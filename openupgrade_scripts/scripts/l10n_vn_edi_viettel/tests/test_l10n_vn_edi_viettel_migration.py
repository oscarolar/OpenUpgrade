from odoo.tests import TransactionCase, tagged

from odoo.addons.openupgrade_framework import openupgrade_test


@tagged("-at_install", "post_install")
@openupgrade_test
class TestL10nVnEdiViettelMigration(TransactionCase):
    def setUp(self):
        super().setUp()
        self.companies = self.env["res.company"].search(
            [("name", "in", ("OU20 VN A", "OU20 VN B"))], order="id"
        )
        if len(self.companies) != 2:
            self.skipTest("data_l10n_vn_edi_viettel_migration.py was not loaded")
        self.symbols = (
            self.env["l10n_vn_edi_viettel.sinvoice.symbol"]
            .with_context(active_test=False)
            .search([("name", "=", "K26TOU")])
        )

    def test_one_symbol_per_company(self):
        self.assertEqual(len(self.symbols), 2)
        self.assertEqual(self.symbols.company_id, self.companies)
        self.assertEqual(set(self.symbols.mapped("invoice_template_code")), {"1/OU20"})

    def test_company_records_use_their_symbol(self):
        for company in self.companies:
            symbol = self.symbols.filtered(lambda s, c=company: s.company_id == c)
            move = self.env["account.move"].search(
                [("ref", "=", f"OU20 SInvoice {company.name}")]
            )
            self.assertEqual(move.l10n_vn_edi_invoice_symbol, symbol, company.name)
            self.assertEqual(company.l10n_vn_edi_symbol_id, symbol, company.name)
            if "l10n_vn_pos_default_symbol" in company._fields:
                self.assertEqual(
                    company.l10n_vn_pos_default_symbol, symbol, company.name
                )

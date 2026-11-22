from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestL10nMxMigration(TransactionCase):
    def test_bank_abm_code(self):
        """
        The ABM code of the bank becomes the clearing number of the account
        """
        ResPartnerBank = self.env["res.partner.bank"]
        account = ResPartnerBank.search([("account_number", "=", "002010077777777771")])
        self.assertEqual(account.clearing_number, "002")
        self.assertEqual(
            account.clearing_label_id, self.env.ref("base.clearing_label_mx")
        )
        self.assertEqual(account.bank_name, "BANAMEX")
        self.assertEqual(account.note, "Account number: OU0001234567")
        self.assertFalse(
            ResPartnerBank.search([("account_number", "=", "OU0001234567")])
        )
        clabe_account = ResPartnerBank.search(
            [("account_number", "=", "012180001234567895")]
        )
        self.assertEqual(clabe_account.clearing_number, "012")
        self.assertFalse(clabe_account.note)
        duplicate = ResPartnerBank.search([("account_number", "=", "OU0007654321")])
        self.assertEqual(duplicate.note, "CLABE: 014180001111111117")

    def test_chart_account_groups(self):
        """
        The account groups of the Mexican chart become archived parent accounts
        that keep their xmlids, as the chart of 20.0 expects them
        """
        company = self.env["res.company"].search([("name", "=", "OU MX Company")])
        customers = self.env.ref(f"account.{company.id}_account_subgroup_clientes")
        self.assertEqual(customers._name, "account.account")
        self.assertFalse(customers.active)
        self.assertEqual(customers.with_company(company).code, "105")
        self.assertEqual(customers.name, "Clients")
        self.assertEqual(
            customers.parent_id,
            self.env.ref(f"account.{company.id}_account_group_activos"),
        )
        account = self.env.ref(f"account.{company.id}_cuenta105_01")
        self.assertEqual(
            account.parent_id,
            self.env.ref(f"account.{company.id}_account_subgroup_clientes_nacionales"),
        )
        self.assertIn(customers, account.parent_ids)
        self.assertEqual(
            account.with_company(company).code_path, "1 / 105 / 105.01 / 105.01.01"
        )
        self.assertFalse(
            self.env["ir.model.data"].search_count([("model", "=", "account.group")])
        )
        parent = (
            self.env["account.chart.template"]
            .with_company(company)
            ._get_account_parent_id("102.01.0")
        )
        self.assertEqual(
            parent,
            self.env.ref(f"account.{company.id}_account_subgroup_bancos_nacionales").id,
        )

    def test_quick_edit_mode(self):
        company = self.env["res.company"].search([("name", "=", "OU MX Company")])
        self.assertTrue(company.quick_edit_mode_enabled)
        self.assertEqual(company.quick_edit_mode, "out_invoices")

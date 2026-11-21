from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestAccountMigration(TransactionCase):
    def test_account_group(self):
        """
        Account groups become archived parent accounts
        """
        AccountAccount = self.env["account.account"].with_context(active_test=False)
        parent = AccountAccount.search([("name", "=", "OU group 10")])
        self.assertEqual(len(parent), 1)
        self.assertFalse(parent.active)
        self.assertEqual(parent.code, "10")
        self.assertEqual(parent.parent_id.name, "OU group 1")
        children = AccountAccount.search([("parent_id", "=", parent.id)])
        self.assertTrue(children)
        self.assertTrue(all(child.code.startswith("10") for child in children))

    def test_journal_group(self):
        """
        A journal excluded from all the ledgers but one belongs to that ledger
        """
        AccountJournal = self.env["account.journal"]
        journal_a = AccountJournal.search([("code", "=", "OUA")])
        journal_common = AccountJournal.search([("code", "=", "OUC")])
        self.assertEqual(journal_a.journal_group_id.name, "OU ledger A")
        self.assertFalse(journal_common.journal_group_id)

    def test_payment_state(self):
        AccountPayment = self.env["account.payment"]
        self.assertEqual(
            AccountPayment.search([("memo", "=", "OU payment in_process")]).state,
            "paid",
        )
        self.assertEqual(
            AccountPayment.search([("memo", "=", "OU payment paid")]).state,
            "reconciled",
        )

    def test_move(self):
        AccountMove = self.env["account.move"]
        bill = AccountMove.search([("ref", "=", "OU deductible bill")])
        self.assertEqual(bill.review_state, "no_review")
        self.assertEqual(
            bill.document_tax_mode, bill.company_id.account_price_include
        )
        lines = {
            line.name: line.deductible_percentage for line in bill.invoice_line_ids
        }
        self.assertEqual(lines["OU half deductible"], 0.5)
        self.assertEqual(lines["OU fully deductible"], 1.0)
        entry = AccountMove.search([("ref", "=", "OU entry to review")])
        self.assertEqual(entry.review_state, "todo")
        self.assertFalse(entry.document_tax_mode)

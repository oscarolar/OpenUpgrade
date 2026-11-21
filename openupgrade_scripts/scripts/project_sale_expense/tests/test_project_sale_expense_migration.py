from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestProjectSaleExpenseMigration(TransactionCase):
    def _line(self, name):
        return self.env["account.analytic.line"].search(
            [("name", "=", f"OpenUpgrade v20 {name}")]
        )

    def test_expense_cost(self):
        """
        Test that the analytic lines of expenses get the category and the billable
        type of expenses
        """
        line = self._line("expense cost")
        self.assertEqual(line.category, "expense")
        self.assertEqual(line.billable_type, "13_expense")
        self.assertEqual(line.category_report, "costs")

    def test_expense_revenue(self):
        """
        Test that the analytic lines of a sale order line that is an expense are
        reported as expense revenues
        """
        line = self._line("expense revenue")
        self.assertEqual(line.billable_type, "18_expense_revenues")
        self.assertEqual(line.category_report, "revenues")

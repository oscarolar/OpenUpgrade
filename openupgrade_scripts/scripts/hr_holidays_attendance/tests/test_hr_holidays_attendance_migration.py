from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestHrHolidaysAttendanceMigration(TransactionCase):
    def test_extra_hours_balance(self):
        """
        Test that the balance of deductible extra hours is the same as in v19:
        10 approved compensable hours minus 2 hours of time off
        """
        employee = self.env["hr.employee"].search(
            [("name", "=", "OpenUpgrade v20 extra hours")]
        )
        leave = self.env["hr.leave"].search([("employee_id", "=", employee.id)])
        self.assertEqual(leave.number_of_hours, 2)
        time_type = leave.work_entry_type_id
        self.assertTrue(time_type.requires_allocation)
        allocation = self.env["hr.leave.allocation"].search(
            [
                ("employee_id", "=", employee.id),
                ("work_entry_type_id", "=", time_type.id),
            ]
        )
        self.assertEqual(allocation.state, "validate")
        self.assertAlmostEqual(allocation.number_of_hours, 10)
        self.assertAlmostEqual(
            time_type.with_context(employee_id=employee.id).virtual_remaining_leaves,
            8,
        )

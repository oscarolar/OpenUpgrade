from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestHrHolidaysMigration(TransactionCase):
    def test_time_type_per_country(self):
        """
        Test that a leave type without country stays available for the employees
        of every company, with the same allocated days
        """
        WorkEntryType = self.env["hr.work.entry.type"]
        types = WorkEntryType
        for name in ("main", "be", "stateless"):
            allocation = self.env["hr.leave.allocation"].search(
                [("name", "=", f"OpenUpgrade v20 allocation {name}")]
            )
            self.assertEqual(allocation.state, "validate")
            self.assertEqual(allocation.number_of_days, 5)
            time_type = allocation.work_entry_type_id
            self.assertEqual(time_type.name, "OpenUpgrade v20 shared time off")
            self.assertTrue(time_type.requires_allocation)
            self.assertTrue(time_type.time_off_selectable)
            country = allocation.employee_id.company_id.country_id
            if not WorkEntryType.search_count(
                [("country_id", "=", country.id)], limit=1
            ):
                country = country.browse()
            self.assertEqual(time_type.country_id, country)
            types |= time_type
        self.assertGreater(len(types), 1)

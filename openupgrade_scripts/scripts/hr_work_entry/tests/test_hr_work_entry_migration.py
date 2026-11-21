from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestHrWorkEntryMigration(TransactionCase):
    def test_generic_types(self):
        """
        Test that the generic types get the v20 code and rate
        """
        attendance = self.env.ref("hr_work_entry.generic_work_entry_type_attendance")
        self.assertEqual(attendance.code, "002.00")
        for xmlid in (
            "hr_work_entry.generic_work_entry_type_unpaid_leave",
            "hr_work_entry.generic_hr_work_entry_type_out_of_contract",
        ):
            self.assertEqual(self.env.ref(xmlid).amount_rate, 0.0)

    def test_untouched_types(self):
        """
        Test that the types with the v19 values get the v20 ones
        """
        holiday = self.env.ref("hr_work_entry.l10n_be_work_entry_type_bank_holiday")
        self.assertEqual(holiday.code, "006.00")
        self.assertEqual(holiday.name, "Public holiday")
        self.assertEqual(holiday.display_code, "PH")
        self.assertEqual(holiday.count_as, "absence")
        compensation = self.env.ref(
            "hr_work_entry.l10n_au_work_entry_type_compensation"
        )
        self.assertEqual(compensation.count_as, "absence")

    def test_modified_types(self):
        """
        Test that the values changed by the user and the codes already used in the
        country are kept
        """
        breast_feeding = self.env.ref(
            "hr_work_entry.l10n_be_work_entry_type_breast_feeding"
        )
        self.assertEqual(breast_feeding.code, "LEAVE290")
        self.assertEqual(breast_feeding.name, "Breast-feeding leave")
        self.assertEqual(breast_feeding.amount_rate, 0.0)
        strike = self.env.ref("hr_work_entry.l10n_be_work_entry_type_strike")
        self.assertEqual(strike.name, "OpenUpgrade v20 strike")
        self.assertEqual(strike.code, "132.00")
        extra_legal = self.env.ref("hr_work_entry.l10n_be_work_entry_type_extra_legal")
        self.assertEqual(extra_legal.code, "OU20XL")
        self.assertEqual(extra_legal.name, "Extra-legal holiday")
        maternity = self.env.ref("hr_work_entry.l10n_mx_work_entry_type_maternity_imss")
        self.assertEqual(maternity.amount_rate, 0.5)

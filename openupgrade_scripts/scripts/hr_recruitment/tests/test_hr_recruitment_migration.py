from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestHrRecruitmentMigration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.applicant = cls.env["hr.applicant"].search(
            [("partner_name", "=", "ou19 applicant")]
        )
        cls.employee = cls.env["hr.employee"].search(
            [("user_id.login", "=", "ou19_recruiter")]
        )

    def test_recruiter(self):
        """
        Test that the recruiter user has been replaced by its employee
        """
        self.assertTrue(self.employee)
        self.assertEqual(self.applicant.recruiter_id, self.employee)
        self.assertEqual(self.applicant.job_id.favorite_recruiter_ids, self.employee)

    def test_recruiter_other_company(self):
        """
        Test that the employee of another company is not used as recruiter
        """
        applicant = self.env["hr.applicant"].search(
            [("partner_name", "=", "ou19 applicant of company 2")]
        )
        self.assertTrue(applicant)
        self.assertFalse(applicant.recruiter_id)
        self.assertFalse(applicant.job_id.favorite_recruiter_ids)
        self.assertNotIn("user_id", self.applicant.job_id.alias_defaults)

    def test_properties(self):
        """
        Test that the property definitions of jobs have been moved to companies
        """
        definition = self.applicant.company_id.applicant_properties_definition
        self.assertIn("ou19field", [item["name"] for item in definition])
        self.env.cr.execute(
            "SELECT applicant_properties FROM hr_applicant WHERE id=%s",
            (self.applicant.id,),
        )
        self.assertEqual(self.env.cr.fetchone()[0], {"ou19field": "ou19 value"})

    def test_duration_tracking(self):
        """
        Test that the stored duration tracking points to the current stage
        """
        self.assertEqual(
            self.applicant.duration_tracking["s"], self.applicant.stage_id.id
        )

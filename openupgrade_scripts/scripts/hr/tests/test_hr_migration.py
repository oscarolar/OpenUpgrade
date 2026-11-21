from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestHrMigration(TransactionCase):
    def _employee(self, name):
        return (
            self.env["hr.employee"]
            .with_context(active_test=False)
            .search([("name", "=", f"OpenUpgrade v20 {name}")])
        )

    def test_employee_type(self):
        """
        Test that the employee type comes from the contract type, else from the
        removed selection
        """
        self.assertEqual(self._employee("worker").employee_type_id.name, "Worker")
        self.assertEqual(
            self._employee("student").employee_type_id,
            self.env.ref("hr.contract_type_student"),
        )
        self.assertEqual(
            self._employee("permanent").employee_type_id,
            self.env.ref("hr.contract_type_permanent"),
        )
        self.assertFalse(
            self.env.ref("hr.contract_type_statutory", raise_if_not_found=False)
        )

    def test_version_fields(self):
        """
        Test the fields that moved between employee and version
        """
        worker = self._employee("worker")
        self.assertEqual(worker.additional_note, "OpenUpgrade v20 note")
        self.assertTrue(worker.fixed_term)
        self.assertFalse(self._employee("student").fixed_term)
        self.assertEqual(self._employee("flexible").tz, "America/Mexico_City")

    def test_fully_flexible(self):
        """
        Test that employees without calendar get a fully flexible one
        """
        flexible = self._employee("flexible")
        self.assertTrue(flexible.resource_calendar_id._is_fully_flexible())
        self.assertEqual(
            flexible.resource_id.calendar_id, flexible.resource_calendar_id
        )

    def test_departure(self):
        """
        Test that departures are created as applied for archived employees
        """
        departed = self._employee("departed")
        self.assertEqual(
            departed.departure_id.departure_reason_id,
            self.env.ref("hr.departure_fired"),
        )
        self.assertEqual(str(departed.departure_date), "2025-06-30")
        self.assertTrue(departed.departure_id.apply_date)
        self.assertFalse(departed.fixed_term)
        leaving = self._employee("leaving")
        self.assertTrue(leaving.active)
        self.assertEqual(str(leaving.departure_id.departure_date), "2099-01-01")
        self.assertFalse(leaving.departure_id.apply_date)
        self.assertFalse(self._employee("stayed").departure_id)

    def test_job(self):
        """
        Test that jobs have a company and the recruiter is the employee of the user
        """
        job = self.env["hr.job"].search([("name", "=", "OpenUpgrade v20 job")])
        self.assertTrue(job.company_id)
        self.assertEqual(job.recruiter_id, self._employee("recruiter"))
        job = self.env["hr.job"].search(
            [("name", "=", "OpenUpgrade v20 job of company 2")]
        )
        self.assertFalse(job.recruiter_id)

    def test_job_company(self):
        """
        Test that jobs without company are merged into the job with the same name
        and department, and copied for every company that uses them
        """
        Job = self.env["hr.job"].with_context(active_test=False)
        job = Job.search([("name", "=", "OpenUpgrade v20 duplicated job")])
        self.assertEqual(len(job), 1)
        self.assertEqual(self._employee("duplicated job").job_id, job)
        jobs = Job.search([("name", "=", "OpenUpgrade v20 shared job")])
        self.assertEqual(len(jobs), 2)
        for name in ("shared job 1", "shared job 2"):
            employee = self._employee(name)
            self.assertIn(employee.job_id, jobs)
            self.assertEqual(employee.job_id.company_id, employee.company_id)

    def test_plan_template(self):
        """
        Test that templates assigned to the coach survive
        """
        template = self.env["mail.activity.plan.template"].search(
            [("summary", "=", "OpenUpgrade v20 coach template")]
        )
        self.assertEqual(template.responsible_type, "on_demand")

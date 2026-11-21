from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestHrSkillsMigration(TransactionCase):
    def test_certification_activity_type(self):
        """
        Test that what used the removed certification type uses the upload one
        """
        self.assertFalse(
            self.env.ref(
                "hr_skills.mail_activity_data_upload_certification",
                raise_if_not_found=False,
            )
        )
        upload = self.env.ref("mail.mail_activity_data_upload_document")
        template = self.env["mail.activity.plan.template"].search(
            [("summary", "=", "OpenUpgrade v20 certification template")]
        )
        self.assertEqual(template.activity_type_id, upload)
        action = self.env["ir.actions.server"].search(
            [("name", "=", "OpenUpgrade v20 certification action")]
        )
        self.assertEqual(action.activity_type_id, upload)

    def test_certificate_filename(self):
        """
        Test that the name of the certificate is kept on its attachment
        """
        line = self.env["hr.resume.line"].search(
            [("name", "=", "OpenUpgrade v20 resume line")]
        )
        attachment = (
            self.env["ir.attachment"]
            .sudo()
            .search(
                [
                    ("res_model", "=", "hr.resume.line"),
                    ("res_field", "=", "certificate_file"),
                    ("res_id", "=", line.id),
                ]
            )
        )
        self.assertEqual(attachment.name, "ou20_certificate.pdf")

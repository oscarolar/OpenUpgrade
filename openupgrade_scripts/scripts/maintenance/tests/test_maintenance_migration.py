from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestMaintenanceMigration(TransactionCase):
    def _request(self, name):
        return self.env["maintenance.request"].search(
            [("name", "=", f"OpenUpgrade v20 {name}")]
        )

    def test_instruction_pdf(self):
        """
        Test that the PDF is a regular attachment and the hidden text is kept
        """
        request = self._request("pdf")
        attachment = self.env["ir.attachment"].search(
            [
                ("res_model", "=", "maintenance.request"),
                ("res_id", "=", request.id),
            ]
        )
        self.assertEqual(len(attachment), 1)
        self.assertFalse(attachment.res_field)
        self.assertTrue(attachment.name.endswith(".pdf"))
        self.assertIn("OpenUpgrade v20 hidden text", request.instruction_text)

    def test_instruction_google_slide(self):
        """
        Test that only http(s) links become a link, escaped
        """
        text = self._request("google slide").instruction_text
        self.assertIn(
            '<a href="https://docs.google.com/x?a=1&amp;b=&lt;2&gt;">', str(text)
        )
        text = self._request("bad google slide").instruction_text
        self.assertNotIn("<a", str(text))
        self.assertIn("javascript:alert(1)", str(text))

    def test_state(self):
        """
        Test that archived requests in a done stage are cancelled
        """
        self.assertEqual(self._request("archived done").state, "cancelled")
        self.assertEqual(self._request("done").state, "done")

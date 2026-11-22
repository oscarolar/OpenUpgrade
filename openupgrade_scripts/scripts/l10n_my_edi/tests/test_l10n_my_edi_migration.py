import importlib.util
import os

from odoo.tests import TransactionCase, tagged

from odoo.addons.openupgrade_framework import openupgrade_test


def _load_script(addon, version, script):
    path = os.path.join(
        os.path.dirname(__file__), os.pardir, os.pardir, addon, version, script
    )
    spec = importlib.util.spec_from_file_location(f"ou20_{addon}_{version}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("-at_install", "post_install")
@openupgrade_test
class TestL10nMyEdiMigration(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env["res.company"].search([("name", "=", "OU20 MY EDI")])
        if not self.company:
            self.skipTest("data_l10n_my_edi_migration.py was not loaded")
        self.documents = self.env["myinvois.document"].search(
            [("company_id", "=", self.company.id)]
        )
        self.script = _load_script("l10n_my_edi", "20.0.1.0", "post-migration.py")
        self.pos_script = _load_script(
            "l10n_my_edi_pos", "20.0.1.0", "post-migration.py"
        )

    def _document(self, ref):
        move = self.env["account.move"].search([("ref", "=", ref)])
        return self.documents.filtered(lambda doc: move in doc.invoice_ids)

    def _journal(self, journal_type):
        return self.env["account.journal"].search(
            [("company_id", "=", self.company.id), ("type", "=", journal_type)],
            limit=1,
        )

    def _state(self):
        self.env.invalidate_all()
        return sorted(
            self.env["myinvois.document"]
            .search([])
            .mapped(
                lambda doc: (
                    doc.id,
                    doc.move_type,
                    doc.journal_id.id,
                    doc.is_consolidated_invoice,
                    doc.is_debit_note,
                )
            )
        )

    def test_invoice_documents(self):
        sale = self._journal("sale")
        expected = {
            "OU20 MY single": ("out_invoice", sale, False, False),
            "OU20 MY refund": ("out_refund", sale, False, False),
            "OU20 MY debit": ("out_invoice", sale, False, True),
            "OU20 MY bill": ("in_invoice", self._journal("purchase"), False, False),
            "OU20 MY consolidated 1": ("out_invoice", sale, True, False),
        }
        for ref, (move_type, journal, consolidated, debit) in expected.items():
            document = self._document(ref)
            self.assertEqual(len(document), 1, ref)
            self.assertEqual(document.move_type, move_type, ref)
            self.assertEqual(document.journal_id, journal, ref)
            self.assertEqual(document.is_consolidated_invoice, consolidated, ref)
            self.assertEqual(document.is_debit_note, debit, ref)
        self.assertEqual(
            self._document("OU20 MY consolidated 1"),
            self._document("OU20 MY consolidated 2"),
        )

    def test_pos_document(self):
        if "pos_order_ids" not in self.documents._fields:
            self.skipTest("l10n_my_edi_pos is not installed")
        document = self.documents.filtered("pos_order_ids")
        self.assertEqual(len(document), 1)
        self.assertEqual(document.move_type, "out_invoice")
        self.assertEqual(document.journal_id, document.pos_config_id.journal_id)
        self.assertTrue(document.journal_id)
        self.assertTrue(document.is_consolidated_invoice)

    def test_required_columns(self):
        self.env.cr.execute(
            """
            SELECT column_name, is_nullable FROM information_schema.columns
            WHERE table_name = 'myinvois_document'
                AND column_name IN ('move_type', 'journal_id')
            """
        )
        self.assertEqual(
            dict(self.env.cr.fetchall()), {"move_type": "NO", "journal_id": "NO"}
        )

    def test_rerun_does_not_duplicate(self):
        before = self._state()
        self.script._myinvois_document_invoice_values(self.env)
        self.pos_script._myinvois_document_pos_values(self.env)
        self.assertEqual(self._state(), before)

    def test_database_without_data(self):
        self.env.cr.execute("DELETE FROM myinvois_document")
        self.script._myinvois_document_invoice_values(self.env)
        self.pos_script._myinvois_document_pos_values(self.env)
        self.env.invalidate_all()
        self.assertFalse(self.env["myinvois.document"].search([]))

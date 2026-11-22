import importlib.util
import os

from odoo.tests import TransactionCase, tagged

from odoo.addons.openupgrade_framework import openupgrade_test


def _load_script(version, script):
    path = os.path.join(os.path.dirname(__file__), os.pardir, version, script)
    spec = importlib.util.spec_from_file_location(f"ou20_sii_{version}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("-at_install", "post_install")
@openupgrade_test
class TestL10nEsEdiSiiMigration(TransactionCase):
    def setUp(self):
        super().setUp()
        self.moves = self.env["account.move"].search([("ref", "like", "OU20 SII %")])
        if not self.moves:
            self.skipTest("data_l10n_es_edi_sii_migration.py was not loaded")

    def _move(self, ref):
        return self.moves.filtered(lambda move: move.ref == ref)

    def test_documents_keep_their_state(self):
        expected = {
            "OU20 SII sent": ("accepted", "sent", "CSV-OU20-SENT"),
            "OU20 SII warning": (
                "accepted_with_errors",
                "accepted_with_errors",
                "CSV-OU20-WARN",
            ),
            "OU20 SII to cancel": ("to_cancel", "to_cancel", "CSV-OU20-TOCANCEL"),
            "OU20 SII cancelled": ("cancelled", "cancelled", "CSV-OU20-CANCELLED"),
            "OU20 SII error": ("to_send", "to_send", False),
        }
        for ref, (doc_state, move_state, csv) in expected.items():
            move = self._move(ref)
            documents = move.l10n_es_edi_sii_document_ids
            self.assertEqual(len(documents), 1, ref)
            self.assertEqual(documents.state, doc_state, ref)
            self.assertEqual(move.l10n_es_edi_sii_state, move_state, ref)
            self.assertEqual(move.l10n_es_edi_csv, csv, ref)

    def test_sent_documents_keep_their_payload(self):
        for ref in ("OU20 SII sent", "OU20 SII warning", "OU20 SII cancelled"):
            document = self._move(ref).l10n_es_edi_sii_document_ids
            self.assertTrue(document.attachment_id.exists(), ref)
            self.assertIn(ref.encode(), bytes(document.attachment_id.raw))

    def test_sent_invoices_are_not_sent_again(self):
        for ref in ("OU20 SII sent", "OU20 SII warning"):
            move = self._move(ref)
            self.assertFalse(move.l10n_es_edi_sii_state in ("to_send", False), ref)

    def test_generic_documents_removed(self):
        self.assertFalse(
            self.env["account.edi.document"].search(
                [("edi_format_id.code", "=", "es_sii")]
            )
        )
        self.assertFalse(
            self.env.ref("l10n_es_edi_sii.edi_es_sii", raise_if_not_found=False)
        )

    def test_rerun_does_not_duplicate(self):
        count = self.env["l10n_es_edi_sii.document"].search_count([])
        _load_script("20.0.1.1", "post-migration.py")._l10n_es_edi_sii_document(
            self.env
        )
        self.env.invalidate_all()
        self.assertEqual(self.env["l10n_es_edi_sii.document"].search_count([]), count)

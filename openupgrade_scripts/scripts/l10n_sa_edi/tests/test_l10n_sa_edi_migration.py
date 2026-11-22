import importlib.util
import os

from odoo.tests import TransactionCase, tagged

from odoo.addons.openupgrade_framework import openupgrade_test


def _load_script(version, script):
    path = os.path.join(os.path.dirname(__file__), os.pardir, version, script)
    spec = importlib.util.spec_from_file_location(f"ou20_zatca_{version}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("-at_install", "post_install")
@openupgrade_test
class TestL10nSaEdiMigration(TransactionCase):
    def setUp(self):
        super().setUp()
        self.moves = self.env["account.move"].search([("ref", "like", "OU20 ZATCA %")])
        if not self.moves:
            self.skipTest("data_l10n_sa_edi_migration.py was not loaded")

    def _move(self, ref):
        return self.moves.filtered(lambda move: move.ref == ref)

    def test_documents_keep_their_state_and_chain(self):
        expected = {
            "OU20 ZATCA accepted": ("accepted", 1),
            "OU20 ZATCA warning": ("warning", 2),
            "OU20 ZATCA timeout": ("to_send", 3),
            "OU20 ZATCA rejected": ("rejected", 0),
            "OU20 ZATCA to send": ("to_send", 0),
        }
        for ref, (state, chain_index) in expected.items():
            move = self._move(ref)
            document = move.l10n_sa_edi_document_id
            self.assertTrue(document, ref)
            self.assertEqual(document.state, state, ref)
            self.assertEqual(move.l10n_sa_edi_state, state, ref)
            self.assertEqual(document.l10n_sa_chain_index or 0, chain_index, ref)
            self.assertEqual(document.journal_id, move.journal_id, ref)

    def test_accepted_invoices_keep_their_xml(self):
        for ref in ("OU20 ZATCA accepted", "OU20 ZATCA warning"):
            move = self._move(ref)
            document = move.l10n_sa_edi_document_id
            self.assertTrue(document._l10n_sa_is_in_chain(), ref)
            self.assertTrue(move._l10n_sa_is_legal(), ref)
            self.assertTrue(document.attachment_id.exists(), ref)
            self.assertIn(ref.encode(), bytes(document.attachment_id.raw))

    def test_unknown_documents_can_be_resent(self):
        documents = self.env["l10n_sa_edi.document"].search([("state", "=", "unknown")])
        for document in documents:
            self.assertTrue(document.attachment_id.raw, document.resource.display_name)

    def test_journal_chain_continues(self):
        journal = self._move("OU20 ZATCA accepted").journal_id
        self.assertEqual(journal.l10n_sa_latest_submission_hash, "OU20HASH3")
        self.assertEqual(journal.l10n_sa_chain_sequence_id.number_next_actual, 4)

    def test_company_state(self):
        company = self._move("OU20 ZATCA accepted").company_id
        self.assertEqual(company.state_id, self.env.ref("base.state_sa_001"))

    def test_generic_documents_removed(self):
        self.assertFalse(
            self.env["account.edi.document"].search(
                [("edi_format_id.code", "=", "sa_zatca")]
            )
        )

    def test_rerun_does_not_duplicate(self):
        count = self.env["l10n_sa_edi.document"].search_count([])
        logs = self.env["l10n_sa_edi.log"].search_count([])
        _load_script("20.0.0.3", "post-migration.py")._l10n_sa_edi_document(self.env)
        self.env.invalidate_all()
        self.assertEqual(self.env["l10n_sa_edi.document"].search_count([]), count)
        self.assertEqual(self.env["l10n_sa_edi.log"].search_count([]), logs)

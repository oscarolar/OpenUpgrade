import importlib.util
import os

from odoo.tests import TransactionCase, tagged

from odoo.addons.openupgrade_framework import openupgrade_test


def _load_script(version, script):
    path = os.path.join(os.path.dirname(__file__), os.pardir, version, script)
    spec = importlib.util.spec_from_file_location(f"ou20_eta_{version}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("-at_install", "post_install")
@openupgrade_test
class TestL10nEgEdiEtaMigration(TransactionCase):
    def setUp(self):
        super().setUp()
        self.moves = self.env["account.move"].search([("ref", "like", "OU20 ETA %")])
        if not self.moves:
            self.skipTest("data_l10n_eg_edi_eta_migration.py was not loaded")

    def _move(self, ref):
        return self.moves.filtered(lambda move: move.ref == ref)

    def test_submissions(self):
        expected = {
            "OU20 ETA sent": ("test", "SENT"),
            "OU20 ETA cancelled": ("cancel", "CANCELLED"),
            "OU20 ETA invalid": ("test", "INVALID"),
        }
        for ref, (state, key) in expected.items():
            move = self._move(ref)
            submission = move.l10n_eg_eta_submission_ids
            self.assertEqual(len(submission), 1, ref)
            self.assertEqual(submission.state, state, ref)
            self.assertEqual(submission.eta_document_uuid, f"UUID-OU20-{key}")
            self.assertEqual(submission.eta_submission_id, f"SUB-OU20-{key}")
            self.assertEqual(submission.eta_document_longid, f"LONG-OU20-{key}")
            self.assertEqual(move.l10n_eg_uuid, f"UUID-OU20-{key}")
            self.assertEqual(move.l10n_eg_long_id, f"LONG-OU20-{key}")
            self.assertEqual(move.l10n_eg_edi_submission_state, state, ref)
        self.assertIn(
            "marked as invalid",
            self._move("OU20 ETA invalid").l10n_eg_eta_submission_ids.message,
        )
        move = self._move("OU20 ETA to send")
        self.assertFalse(move.l10n_eg_eta_submission_ids)
        self.assertEqual(move.l10n_eg_edi_submission_state, "to_send")

    def test_company_and_product(self):
        move = self._move("OU20 ETA sent")
        self.assertEqual(move.company_id.l10n_eg_edi_api_mode, "preproduction")
        product = self.env["product.product"].search(
            [("name", "=", "OU20 ETA product")]
        )
        self.assertEqual(
            product.with_company(move.company_id).l10n_eg_eta_code, "EG-OU20-0001"
        )

    def test_generic_documents_removed(self):
        self.assertFalse(
            self.env["account.edi.document"].search(
                [("edi_format_id.code", "=", "eg_eta")]
            )
        )
        self.assertFalse(
            self.env.ref("l10n_eg_edi_eta.edi_eg_eta", raise_if_not_found=False)
        )

    def test_rerun_does_not_duplicate(self):
        count = self.env["l10n_eg_edi.eta.submission"].search_count([])
        _load_script("20.0.0.2", "post-migration.py")._l10n_eg_edi_eta_submission(
            self.env
        )
        self.env.invalidate_all()
        self.assertEqual(self.env["l10n_eg_edi.eta.submission"].search_count([]), count)

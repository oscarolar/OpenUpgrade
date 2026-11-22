import importlib.util
import os

from odoo.tests import TransactionCase, tagged

from odoo.addons.openupgrade_framework import openupgrade_test


def _load_script(version, script):
    path = os.path.join(os.path.dirname(__file__), os.pardir, version, script)
    spec = importlib.util.spec_from_file_location(f"ou20_vf_{version}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("-at_install", "post_install")
@openupgrade_test
class TestL10nEsEdiVerifactuMigration(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env["res.company"].search([("name", "=", "OU20 ES VF")])
        if not self.company:
            self.skipTest("data_l10n_es_edi_verifactu_migration.py was not loaded")
        self.moves = self.env["account.move"].search([("ref", "like", "OU20 VF %")])

    def test_chain_continues(self):
        Issuer = self.env["l10n_es_edi_verifactu.issuer"]
        issuer = Issuer.search([("company_id", "=", self.company.id)])
        self.assertEqual(len(issuer), 1)
        self.assertEqual(issuer.obligado_partner_id, self.company.partner_id)
        self.assertEqual(str(issuer.next_batch_time), "2026-01-15 10:00:00")
        self.assertEqual(issuer.chain_sequence_id.number_next_actual, 4)
        last = issuer._get_last_document()
        self.assertEqual(last.chain_index, 3)
        self.assertEqual(last.move_id.ref, "OU20 VF 3")
        self.assertEqual(
            Issuer._get_or_create(self.company, self.company.partner_id), issuer
        )
        documents = self.moves.l10n_es_edi_verifactu_document_ids
        self.assertEqual(len(documents), 3)
        self.assertEqual(documents.obligado_partner_id, self.company.partner_id)
        self.assertEqual(set(documents.mapped("state")), {"accepted"})

    def test_move_values(self):
        for move in self.moves:
            if move.move_type == "out_refund":
                self.assertEqual(move.l10n_es_invoice_type, "R1")
            else:
                self.assertEqual(move.l10n_es_regime_code, "02_sale")
        self.assertEqual(
            self.company.l10n_es_special_vat_regime, "equivalence_surcharge"
        )

    def test_rerun_does_not_duplicate(self):
        count = self.env["l10n_es_edi_verifactu.issuer"].search_count([])
        _load_script("20.0.1.0", "post-migration.py")._l10n_es_edi_verifactu_issuer(
            self.env
        )
        self.env.invalidate_all()
        self.assertEqual(
            self.env["l10n_es_edi_verifactu.issuer"].search_count([]), count
        )

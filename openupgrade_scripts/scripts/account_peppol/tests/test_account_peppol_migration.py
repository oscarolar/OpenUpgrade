import importlib.util
import os

from odoo.tests import TransactionCase, tagged

from odoo.addons.openupgrade_framework import openupgrade_test


def _load_script(version, script):
    path = os.path.join(os.path.dirname(__file__), os.pardir, version, script)
    spec = importlib.util.spec_from_file_location(f"ou20_peppol_{version}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("-at_install", "post_install")
@openupgrade_test
class TestAccountPeppolMigration(TransactionCase):
    def setUp(self):
        super().setUp()
        self.moves = self.env["account.move"].search([("ref", "like", "OU20 Peppol %")])
        if len(self.moves) != 3:
            self.skipTest("data_account_peppol_migration.py was not loaded")
        self.script = _load_script("20.0.1.2", "pre-migration.py")

    def _state(self):
        self.env.invalidate_all()
        return {move.ref: move.peppol_move_state for move in self.moves}

    def test_skipped_becomes_error(self):
        self.assertEqual(
            self._state(),
            {
                "OU20 Peppol skipped": "error",
                "OU20 Peppol done": "done",
                "OU20 Peppol error": "error",
            },
        )
        self.assertFalse(
            self.env["account.move"].search_count(
                [("peppol_move_state", "=", "skipped")]
            )
        )

    def test_rerun_does_not_duplicate(self):
        before = self._state()
        self.script._account_move_peppol_move_state(self.env)
        self.assertEqual(self._state(), before)

    def test_database_without_data(self):
        self.env.cr.execute("UPDATE account_move SET peppol_move_state = NULL")
        self.script._account_move_peppol_move_state(self.env)
        self.env.invalidate_all()
        self.assertFalse(
            self.env["account.move"].search_count([("peppol_move_state", "!=", False)])
        )

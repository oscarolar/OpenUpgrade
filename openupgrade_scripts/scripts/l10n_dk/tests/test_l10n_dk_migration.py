import importlib.util
import os

from odoo.tests import TransactionCase, tagged

from odoo.addons.openupgrade_framework import openupgrade_test


def _load_script(version, script):
    path = os.path.join(os.path.dirname(__file__), os.pardir, version, script)
    spec = importlib.util.spec_from_file_location(f"ou20_l10n_dk_{version}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("-at_install", "post_install")
@openupgrade_test
class TestL10nDkMigration(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env["res.company"].search([("name", "=", "OU20 DK")])
        if not self.company:
            self.skipTest("data_l10n_dk_migration.py was not loaded")
        self.main = self.env.ref("base.main_company")
        self.script = _load_script("20.0.1.4", "post-migration.py")

    def _partner(self, name):
        return self.env["res.partner"].search([("name", "=", name)])

    def _store(self):
        self.env.cr.execute(
            """
            SELECT name, invoice_edi_format_store FROM res_partner
            WHERE name LIKE 'OU20 DK %%' ORDER BY name
            """
        )
        return self.env.cr.fetchall()

    def _default(self):
        return self.env["ir.default"]._get(
            "res.partner", "invoice_edi_format_store", company_id=self.company.id
        )

    def test_partners_use_oioubl_21(self):
        self.assertEqual(
            dict(self._store()),
            {
                "OU20 DK OIOUBL": {str(self.company.id): "oioubl_21"},
                "OU20 DK mixed": {
                    str(self.company.id): "oioubl_21",
                    str(self.main.id): "ubl_bis3",
                },
                "OU20 DK other": {str(self.company.id): "ubl_bis3"},
            },
        )
        partner = self._partner("OU20 DK OIOUBL").with_company(self.company)
        self.assertEqual(partner.invoice_edi_format, "oioubl_21")
        mixed = self._partner("OU20 DK mixed")
        self.assertEqual(
            mixed.with_company(self.main).invoice_edi_format_store, "ubl_bis3"
        )

    def test_default_uses_oioubl_21(self):
        self.assertEqual(self._default(), "oioubl_21")
        self.env.cr.execute(
            "SELECT COUNT(*) FROM ir_default WHERE json_value = '\"oioubl_201\"'"
        )
        self.assertEqual(self.env.cr.fetchone()[0], 0)

    def test_rerun_does_not_duplicate(self):
        before = (self._store(), self._default())
        self.script._res_partner_invoice_edi_format(self.env)
        self.env.invalidate_all()
        self.assertEqual((self._store(), self._default()), before)

    def test_database_without_data(self):
        self.env.cr.execute(
            "UPDATE res_partner SET invoice_edi_format_store = NULL "
            "WHERE invoice_edi_format_store IS NOT NULL"
        )
        self.env.cr.execute(
            """
            DELETE FROM ir_default USING ir_model_fields imf
            WHERE imf.id = ir_default.field_id
                AND imf.model = 'res.partner'
                AND imf.name = 'invoice_edi_format_store'
            """
        )
        self.script._res_partner_invoice_edi_format(self.env)
        self.env.invalidate_all()
        self.assertFalse(any(store for _name, store in self._store()))

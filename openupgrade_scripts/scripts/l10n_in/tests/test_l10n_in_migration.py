import importlib.util
import os

from odoo.tests import TransactionCase, tagged

from odoo.addons.openupgrade_framework import openupgrade_test


def _load_script(version, script):
    path = os.path.join(os.path.dirname(__file__), os.pardir, version, script)
    spec = importlib.util.spec_from_file_location(f"ou20_l10n_in_{version}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("-at_install", "post_install")
@openupgrade_test
class TestL10nInMigration(TransactionCase):
    def setUp(self):
        super().setUp()
        self.companies = self.env["res.company"].search(
            [("name", "in", ("OU20 IN GST", "OU20 IN NOGST"))], order="name"
        )
        if len(self.companies) != 2:
            self.skipTest("data_l10n_in_migration.py was not loaded")
        self.gst, self.nogst = self.companies
        self.script = _load_script("20.0.2.2", "post-migration.py")

    def _taxes(self, domain):
        return (
            self.env["account.tax"]
            .with_context(active_test=False)
            .search([("company_id", "in", self.companies.ids), *domain])
        )

    def _state(self):
        self.env.invalidate_all()
        taxes = self._taxes([("l10n_in_tax_type", "=", "tds")])
        pan = self.env["l10n_in.pan.entity"].search([("name", "=", "AAAPL1234C")])
        return (
            self.companies.mapped("l10n_in_gst_registration_type"),
            sorted(
                taxes.mapped(lambda t: (t.id, t.type_tax_use, t.is_withholding_tax))
            ),
            self.env["ir.attachment"].search_count(
                [("res_model", "=", "l10n_in.pan.entity"), ("res_id", "=", pan.id)]
            ),
            pan.tds_certificate.filename,
        )

    def test_gst_registration_type(self):
        self.assertEqual(self.gst.l10n_in_gst_registration_type, "regular")
        self.assertFalse(self.nogst.l10n_in_gst_registration_type)

    def test_tds_taxes_are_withholding_taxes(self):
        self.assertFalse(
            self._taxes([("l10n_in_tax_type", "in", ("tds_sale", "tds_purchase"))])
        )
        for company in self.companies:
            for use in ("sale", "purchase"):
                taxes = self._taxes(
                    [
                        ("company_id", "=", company.id),
                        ("l10n_in_tax_type", "=", "tds"),
                        ("type_tax_use", "=", use),
                    ]
                )
                self.assertEqual(len(taxes), 129, (company.name, use))
                self.assertTrue(all(taxes.mapped("is_withholding_tax")))
                self.assertTrue(all(amount < 0 for amount in taxes.mapped("amount")))
            sale = self.env.ref(f"account.{company.id}_tds_sale_5_us_392_1")
            self.assertEqual(sale.type_tax_use, "sale")
            self.assertEqual(sale.l10n_in_tax_type, "tds")
            self.assertTrue(sale.is_withholding_tax)
        self.assertFalse(
            self._taxes(
                [("l10n_in_tax_type", "!=", "tds"), ("is_withholding_tax", "=", True)]
            )
        )

    def test_tds_certificate_keeps_its_name(self):
        pan = self.env["l10n_in.pan.entity"].search([("name", "=", "AAAPL1234C")])
        self.assertEqual(pan.tds_certificate.filename, "ou20_tds_certificate.pdf")
        self.assertEqual(pan.tds_certificate.content, b"%PDF-1.4 OU20 TDS certificate")
        other = self.env["l10n_in.pan.entity"].search([("name", "=", "BBBPL1234C")])
        self.assertFalse(other.tds_certificate)

    def test_rerun_does_not_duplicate(self):
        before = self._state()
        self.script._res_company_l10n_in_gst_registration_type(self.env)
        self.script._account_tax_tds(self.env)
        self.script._l10n_in_pan_entity_tds_certificate_filename(self.env)
        self.assertEqual(self._state(), before)

    def test_database_without_data(self):
        self.env.cr.execute(
            "UPDATE res_company SET l10n_in_is_gst_registered = NULL, "
            "l10n_in_gst_registration_type = NULL"
        )
        self.env.cr.execute(
            "UPDATE account_tax SET l10n_in_tax_type = NULL, is_withholding_tax = FALSE"
        )
        self.env.cr.execute("DELETE FROM l10n_in_pan_entity")
        self.script._res_company_l10n_in_gst_registration_type(self.env)
        self.script._account_tax_tds(self.env)
        self.script._l10n_in_pan_entity_tds_certificate_filename(self.env)
        self.env.invalidate_all()
        self.assertFalse(
            self.env["res.company"].search(
                [("l10n_in_gst_registration_type", "!=", False)]
            )
        )
        self.assertFalse(self._taxes([("is_withholding_tax", "=", True)]))

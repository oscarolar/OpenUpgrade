from odoo.tests import tagged

from odoo.addons.openupgrade_framework import openupgrade_test

# pylint: disable=odoo-addons-relative-import
from odoo.addons.openupgrade_scripts import l10n_tax_tags_testing as testing


@tagged("-at_install", "post_install")
@openupgrade_test
class TestL10nThMigration(testing.L10nTaxTagsCase):
    country = "th"
    template_code = "th"

    def setUp(self):
        super().setUp()
        self.script = testing.load_script("l10n_th", "20.0.2.0", "post-migration.py")

    def test_tax_tags(self):
        outcome = self.tax_outcome()
        self.assertEqual(
            outcome["retagged"],
            {"tax_output_vat", "tax_output_vat_0", "tax_output_vat_exempted"},
        )
        sale = self.env.ref(f"account.{self.company.id}_tax_output_vat")
        self.assertNotIn(
            "1. Sales amount", self._names(sale.repartition_line_ids.tag_ids)
        )

    def test_move_lines(self):
        self.check_move_lines()

    def test_obsolete_report_data(self):
        self.check_obsolete_report_data("l10n_th", self.script)

    def test_rerun_does_nothing(self):
        self.check_rerun(self.script)

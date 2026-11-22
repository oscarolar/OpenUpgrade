from odoo.tests import tagged

from odoo.addons.openupgrade_framework import openupgrade_test

# pylint: disable=odoo-addons-relative-import
from odoo.addons.openupgrade_scripts import l10n_tax_tags_testing as testing


@tagged("-at_install", "post_install")
@openupgrade_test
class TestL10nEgMigration(testing.L10nTaxTagsCase):
    country = "eg"
    template_code = "eg"

    def setUp(self):
        super().setUp()
        self.script = testing.load_script("l10n_eg", "20.0.1.0", "post-migration.py")

    def test_tax_tags(self):
        outcome = self.tax_outcome()
        self.assertEqual(
            outcome["retagged"],
            {
                "eg_standard_sale_14",
                "eg_standard_purchase_14",
                "eg_zero_sale_0",
                "eg_zero_purchase_0",
                "eg_exempt_sale",
                "eg_exempt_purchase",
            },
        )
        self.assertIn("eg_stamp_tax_20_sale", outcome["unchanged"])
        self.assertIn("eg_withholding_1_purchase", outcome["unchanged"])
        sale = self.env.ref(f"account.{self.company.id}_eg_standard_sale_14")
        self.assertEqual(self._names(sale.repartition_line_ids.tag_ids), ["1b", "1t"])

    def test_move_lines(self):
        self.check_move_lines()

    def test_obsolete_report_data(self):
        self.check_obsolete_report_data("l10n_eg", self.script)

    def test_rerun_does_nothing(self):
        self.check_rerun(self.script)

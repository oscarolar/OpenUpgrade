from odoo.tests import tagged

from odoo.addons.openupgrade_framework import openupgrade_test

# pylint: disable=odoo-addons-relative-import
from odoo.addons.openupgrade_scripts import l10n_tax_tags_testing as testing


@tagged("-at_install", "post_install")
@openupgrade_test
class TestL10nSiMigration(testing.L10nTaxTagsCase):
    country = "si"
    template_code = "si"

    def setUp(self):
        super().setUp()
        self.script = testing.load_script("l10n_si", "20.0.1.1", "post-migration.py")

    def test_recapitulative_tags_stay(self):
        outcome = self.tax_outcome()
        self.assertFalse(outcome["retagged"])
        tax = self.env.ref(f"account.{self.company.id}_gd_taxe_out_0_eu_goods_1")
        self.assertIn(
            "rp_a3",
            self._names(
                tax.repartition_line_ids.filtered(
                    lambda line: line.repartition_type == "base"
                ).tag_ids
            ),
        )
        tag = self.env.ref("l10n_si.account_account_tag_l10n_si_rp_A3")
        self.assertTrue(tag.active)

    def test_move_lines(self):
        self.check_move_lines()

    def test_rerun_does_nothing(self):
        self.assertFalse(self.script._account_account_tag_keep_used(self.env))

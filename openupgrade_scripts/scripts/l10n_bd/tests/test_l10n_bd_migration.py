from odoo.tests import tagged

from odoo.addons.openupgrade_framework import openupgrade_test

# pylint: disable=odoo-addons-relative-import
from odoo.addons.openupgrade_scripts import l10n_tax_tags_testing as testing


@tagged("-at_install", "post_install")
@openupgrade_test
class TestL10nBdMigration(testing.L10nTaxTagsCase):
    country = "bd"
    template_code = "bd"

    def setUp(self):
        super().setUp()
        self.script = testing.load_script("l10n_bd", "20.0.1.0", "post-migration.py")

    def test_tax_tags(self):
        self.assertFalse(self.tax_outcome()["retagged"])

    def test_move_lines(self):
        self.check_move_lines()

    def test_obsolete_report_data(self):
        self.check_obsolete_report_data("l10n_bd", self.script)

    def test_rerun_does_nothing(self):
        self.check_rerun(self.script)

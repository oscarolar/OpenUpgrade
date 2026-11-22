from odoo.tests import tagged

from odoo.addons.openupgrade_framework import openupgrade_test

# pylint: disable=odoo-addons-relative-import
from odoo.addons.openupgrade_scripts import l10n_tax_tags_testing as testing


@tagged("-at_install", "post_install")
@openupgrade_test
class TestL10nPkMigration(testing.L10nTaxTagsCase):
    country = "pk"
    template_code = "pk"

    def setUp(self):
        super().setUp()
        self.script = testing.load_script("l10n_pk", "20.0.1.1", "post-migration.py")

    def test_tax_tags(self):
        self.assertFalse(self.tax_outcome()["retagged"])

    def test_move_lines(self):
        self.check_move_lines()

    def test_obsolete_report_data(self):
        self.check_obsolete_report_data("l10n_pk", self.script)

    def test_rerun_does_nothing(self):
        self.check_rerun(self.script)

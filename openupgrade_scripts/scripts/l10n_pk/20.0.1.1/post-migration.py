# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

# pylint: disable=odoo-addons-relative-import
from odoo.addons.openupgrade_scripts.l10n_tax_tags import migrate_obsolete_tax_tags

_obsolete_reports = (
    "l10n_pk_vat_form",
    "l10n_pk_wh_vat_form",
)


def _tax_tags(env):
    """
    The VAT and withholding reports move out of the module and the taxes of the
    new template have no tags: keep the tags on the taxes and the journal items
    """
    return migrate_obsolete_tax_tags(env, "l10n_pk", ("pk",), reports=_obsolete_reports)


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "l10n_pk", "20.0.1.1/noupdate_changes.xml")
    _tax_tags(env)

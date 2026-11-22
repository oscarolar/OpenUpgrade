# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

# pylint: disable=odoo-addons-relative-import
from odoo.addons.openupgrade_scripts.l10n_tax_tags import migrate_obsolete_tax_tags

_obsolete_reports = ("tr_form",)


def _tax_tags(env):
    """
    The tax report moves out of the module and the taxes of the new template
    have no tags: keep the tags on the taxes and the journal items
    """
    return migrate_obsolete_tax_tags(env, "l10n_bd", ("bd",), reports=_obsolete_reports)


@openupgrade.migrate()
def migrate(env, version):
    _tax_tags(env)

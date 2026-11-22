# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

# pylint: disable=odoo-addons-relative-import
from odoo.addons.openupgrade_scripts.l10n_tax_tags import migrate_obsolete_tax_tags

_obsolete_reports = ("tax_report",)


def _tax_tags(env):
    """
    The tax report is replaced by form 01/GTGT with new tags: the taxes of the
    template take the new tags, the other taxes keep theirs
    """
    return migrate_obsolete_tax_tags(env, "l10n_vn", ("vn",), reports=_obsolete_reports)


@openupgrade.migrate()
def migrate(env, version):
    _tax_tags(env)

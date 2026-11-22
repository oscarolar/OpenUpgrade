# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

# pylint: disable=odoo-addons-relative-import
from odoo.addons.openupgrade_scripts.l10n_tax_tags import migrate_obsolete_tax_tags

_obsolete_reports = (
    "tax_report_pnd3",
    "tax_report_pnd53",
)


def _tax_tags(env):
    """
    The PND3 and PND53 reports are dropped, their tags are module data now and
    the template still uses them: the deletion of the reports must not strip
    them from the taxes nor delete them
    """
    return migrate_obsolete_tax_tags(env, "l10n_th", ("th",), reports=_obsolete_reports)


@openupgrade.migrate()
def migrate(env, version):
    _tax_tags(env)

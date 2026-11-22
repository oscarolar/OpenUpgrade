# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

# pylint: disable=odoo-addons-relative-import
from odoo.addons.openupgrade_scripts.l10n_tax_tags import migrate_obsolete_tax_tags

_obsolete_expressions = (
    "account_tax_report_2B13_base_tag",
    "account_tax_report_2B14_base_tag",
    "account_tax_report_3_18_tax_tag",
    "account_tax_report_3_19_tax_tag",
)


def _tax_tags(env):
    """
    The 8% and 9% lines leave the tax report: the taxes that still use their
    tags keep them
    """
    return migrate_obsolete_tax_tags(
        env, "l10n_do", ("do",), expressions=_obsolete_expressions
    )


@openupgrade.migrate()
def migrate(env, version):
    _tax_tags(env)

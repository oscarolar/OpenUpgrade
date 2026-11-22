# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

# pylint: disable=odoo-addons-relative-import
from odoo.addons.openupgrade_scripts.l10n_tax_tags import migrate_obsolete_tax_tags

_obsolete_expressions = (
    "l10n_kr_general_tp_vat_bt1_balance",
    "l10n_kr_general_tp_vat_bt2_balance",
    "l10n_kr_general_tp_vat_bt3_balance",
    "l10n_kr_general_tp_vat_ime_balance",
    "l10n_kr_general_tp_vat_otzro_tax",
    "l10n_kr_general_tp_vat_otzrtii_tax",
    "l10n_kr_simplified_tp_vat_sbt1_balance",
    "l10n_kr_simplified_tp_vat_sbt2_balance",
    "l10n_kr_simplified_tp_vat_sbt3_balance",
    "l10n_kr_simplified_tp_vat_sbt4_balance",
    "l10n_kr_simplified_tp_vat_sbto_balance",
    "l10n_kr_simplified_tp_vat_siae_balance",
)


def _tax_tags(env):
    """
    Some lines of the general and simplified VAT reports are replaced by new
    tags: the taxes of the template take the new tags, the other taxes keep
    theirs
    """
    return migrate_obsolete_tax_tags(
        env, "l10n_kr", ("kr",), expressions=_obsolete_expressions
    )


@openupgrade.migrate()
def migrate(env, version):
    _tax_tags(env)

# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_old_model = "l10n_tr_nilvera_einvoice_extended.tax.office"
_old_table = "l10n_tr_nilvera_einvoice_extended_tax_office"


def _l10n_tr_tax_office(env):
    """
    The tax offices move here from l10n_tr_nilvera_einvoice_extended, with a
    new model name and shorter xmlids. Rename model, table and xmlids so that
    the existing records, and the partners and companies that point to them,
    are kept instead of loading a second set.
    """
    if not openupgrade.table_exists(env.cr, _old_table):
        return
    openupgrade.rename_models(env.cr, [(_old_model, "l10n_tr.tax.office")])
    openupgrade.rename_tables(env.cr, [(_old_table, "l10n_tr_tax_office")])
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_model_data
        SET module = 'l10n_tr',
            name = replace(
                name, 'l10n_tr_nilvera_einvoice_extended_tax_office_', 'tax_office_'
            )
        WHERE model = 'l10n_tr.tax.office'
            AND module IN (
                'l10n_tr_nilvera_einvoice', 'l10n_tr_nilvera_einvoice_extended'
            )
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_model_data
        SET module = 'l10n_tr'
        WHERE name = 'l10n_tr_menu_state_office_partner'
            AND model = 'ir.ui.menu'
            AND module IN (
                'l10n_tr_nilvera_einvoice', 'l10n_tr_nilvera_einvoice_extended'
            )
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _l10n_tr_tax_office(env)

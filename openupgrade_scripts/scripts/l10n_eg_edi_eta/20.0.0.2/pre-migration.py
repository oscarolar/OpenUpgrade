# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _product_product_l10n_eg_eta_code(env):
    env.cr.execute(
        """
        SELECT data_type FROM information_schema.columns
        WHERE table_name = 'product_product' AND column_name = 'l10n_eg_eta_code'
        """
    )
    row = env.cr.fetchone()
    if row and row[0] != "jsonb":
        openupgrade.rename_columns(
            env.cr, {"product_product": [("l10n_eg_eta_code", None)]}
        )


@openupgrade.migrate()
def migrate(env, version):
    _product_product_l10n_eg_eta_code(env)

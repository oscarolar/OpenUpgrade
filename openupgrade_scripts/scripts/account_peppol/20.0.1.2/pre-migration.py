# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _account_move_peppol_move_state(env):
    """
    account.move#peppol_move_state lost the 'skipped' value, which 19.0 already
    replaced by a regular error
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_move
        SET peppol_move_state = 'error'
        WHERE peppol_move_state = 'skipped'
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _account_move_peppol_move_state(env)

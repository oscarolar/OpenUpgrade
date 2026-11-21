# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def mailing_list_merge_action(env):
    """
    Delete the window action of the removed merge wizard, its xmlid is reused by a
    server action
    """
    openupgrade.logged_query(
        env.cr,
        """
        DELETE FROM ir_act_window
        WHERE id IN (
            SELECT res_id FROM ir_model_data
            WHERE module='mass_mailing' AND name='mailing_list_merge_action'
            AND model='ir.actions.act_window'
        )
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        DELETE FROM ir_model_data
        WHERE module='mass_mailing' AND name='mailing_list_merge_action'
        AND model='ir.actions.act_window'
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    mailing_list_merge_action(env)

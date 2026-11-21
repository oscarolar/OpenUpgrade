# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def crm_team_member_assignment_optout(env):
    """
    Members with paused assignment are out of rotation, which is a capacity of zero
    leads now
    """
    openupgrade.logged_query(
        env.cr,
        "UPDATE crm_team_member SET assignment_max=0 WHERE assignment_optout",
    )


@openupgrade.migrate()
def migrate(env, version):
    crm_team_member_assignment_optout(env)

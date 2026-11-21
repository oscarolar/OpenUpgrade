# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def mail_activity_plan_template_responsible_type(env):
    """
    The responsible type 'fleet_manager' is removed, ask for the responsible at launch
    as its ondelete policy (set default) would have done
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            mail_activity_plan_template
        SET
            responsible_type='on_demand'
        WHERE
            responsible_type='fleet_manager'
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    mail_activity_plan_template_responsible_type(env)

# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _analytic_plan_projects_name(env):
    """
    The project plan is now called 'Project Plan': rename it only when it still
    has its default name, a plan renamed by the user keeps its name.
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_analytic_plan aap
        SET name = aap.name || jsonb_build_object('en_US', 'Project Plan')
        FROM ir_model_data imd
        WHERE imd.module = 'analytic'
            AND imd.name = 'analytic_plan_projects'
            AND imd.res_id = aap.id
            AND aap.name->>'en_US' = 'Project'
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _analytic_plan_projects_name(env)

# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def project_sharing_portal_rules(env):
    """
    Activate the portal ir.access of the timesheets if there are collaborators, as it
    is created inactive and only toggled when the first collaborator is created
    """
    Collaborator = env["project.collaborator"]
    if Collaborator.search([], limit=1):
        Collaborator._toggle_project_sharing_portal_rules(True)


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "hr_timesheet", "20.0.1.0/noupdate_changes.xml")
    project_sharing_portal_rules(env)

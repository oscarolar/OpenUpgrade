# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def project_project_allowed_internal_user_ids(env):
    """
    Fill project.project#allowed_internal_user_ids with the internal users that follow
    a private project, as access to it does not come from following it anymore
    """
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO project_allowed_internal_users_rel
            (project_project_id, res_users_id)
        SELECT DISTINCT
            project_project.id, res_users.id
        FROM
            project_project
        JOIN
            mail_followers
            ON mail_followers.res_model='project.project'
            AND mail_followers.res_id=project_project.id
        JOIN
            res_users
            ON res_users.partner_id=mail_followers.partner_id
        WHERE
            project_project.privacy_visibility IN ('followers', 'invited_users')
        AND
            res_users.active
        AND
            res_users.share IS NOT TRUE
        AND (
            project_project.company_id IS NULL
            OR EXISTS (
                SELECT 1 FROM res_company_users_rel
                WHERE
                    res_company_users_rel.user_id=res_users.id
                AND
                    res_company_users_rel.cid=project_project.company_id
            )
        )
        ON CONFLICT DO NOTHING
        """,
    )


def project_external_followers(env):
    """
    Portal users only see the projects they collaborate on, not the ones they
    follow anymore. External followers are not made collaborators, as that would
    let them read all the tasks of the project: they keep the tasks they follow
    and the ones losing the project are reported
    """
    env.cr.execute(
        """
        SELECT
            project_project.id,
            project_project.name->>'en_US',
            string_agg(
                res_partner.name || ' (id ' || res_partner.id || ')', ', '
                ORDER BY res_partner.id
            )
        FROM
            project_project
        JOIN
            mail_followers
            ON mail_followers.res_model='project.project'
            AND mail_followers.res_id=project_project.id
        JOIN
            res_partner
            ON res_partner.id=mail_followers.partner_id
        WHERE
            project_project.privacy_visibility IN ('invited_users', 'portal')
        AND
            project_project.is_template IS NOT TRUE
        AND
            EXISTS (
                SELECT 1 FROM res_users
                WHERE
                    res_users.partner_id=mail_followers.partner_id
                AND
                    res_users.share
            )
        AND
            NOT EXISTS (
                SELECT 1 FROM res_users
                WHERE
                    res_users.partner_id=mail_followers.partner_id
                AND
                    res_users.share IS NOT TRUE
            )
        AND
            NOT EXISTS (
                SELECT 1 FROM project_collaborator
                WHERE
                    project_collaborator.project_id=project_project.id
                AND
                    project_collaborator.partner_id=mail_followers.partner_id
            )
        GROUP BY
            project_project.id
        ORDER BY
            project_project.id
        """
    )
    for project_id, name, partners in env.cr.fetchall():
        openupgrade.message(
            env.cr,
            "project",
            "project_project",
            "collaborator_ids",
            "Project %s (id %s): these portal followers don't see the project "
            "in the portal anymore, only the tasks they follow. Share the "
            "project with them to give them access to all its tasks: %s",
            name,
            project_id,
            partners,
        )


def project_sharing_portal_rules(env):
    """
    Activate the project sharing ir.access if there are collaborators, as it is created
    inactive and only toggled when the first collaborator is created
    """
    Collaborator = env["project.collaborator"]
    if Collaborator.search([], limit=1):
        Collaborator._toggle_project_sharing_portal_rules(True)


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "project", "20.0.1.4/noupdate_changes.xml")
    project_project_allowed_internal_user_ids(env)
    project_external_followers(env)
    project_sharing_portal_rules(env)

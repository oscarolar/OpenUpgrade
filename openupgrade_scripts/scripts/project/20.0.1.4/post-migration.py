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


def project_collaborator_followers(env):
    """
    Create a project.collaborator with view access for the external followers of a
    shared project, as portal access to it does not come from following it anymore
    """
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO project_collaborator
            (project_id, partner_id, access_mode,
             create_uid, write_uid, create_date, write_date)
        SELECT DISTINCT
            project_project.id, mail_followers.partner_id, 'view',
            1, 1, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC'
        FROM
            project_project
        JOIN
            mail_followers
            ON mail_followers.res_model='project.project'
            AND mail_followers.res_id=project_project.id
        WHERE
            project_project.privacy_visibility IN ('invited_users', 'portal')
        AND
            project_project.is_template IS NOT TRUE
        AND
            mail_followers.partner_id IS NOT NULL
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
        """,
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
    project_collaborator_followers(env)
    project_sharing_portal_rules(env)

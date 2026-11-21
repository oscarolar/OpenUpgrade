# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_added_columns = [
    ("maintenance.request", "state", "selection"),
]


def maintenance_request_state(env):
    """
    Fill maintenance.request#state from archive, the done flag of the stage and
    kanban_state
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            maintenance_request
        SET
            state=CASE
                WHEN maintenance_request.archive IS TRUE THEN 'cancelled'
                WHEN maintenance_stage.done IS TRUE THEN 'done'
                WHEN maintenance_request.kanban_state='blocked'
                    THEN 'changes_requested'
                WHEN maintenance_request.kanban_state='done' THEN 'approved'
                ELSE 'normal'
            END
        FROM
            maintenance_request maintenance_request2
        LEFT JOIN
            maintenance_stage
            ON maintenance_stage.id=maintenance_request2.stage_id
        WHERE
            maintenance_request2.id=maintenance_request.id
        """,
    )


def maintenance_request_user_ids(env):
    """
    Create the relation of maintenance.request#user_ids and fill it from
    maintenance.request#user_id, so that the ORM does not compute it
    """
    openupgrade.logged_query(
        env.cr,
        """
        CREATE TABLE maintenance_request_res_users_rel (
            maintenance_request_id INTEGER NOT NULL,
            res_users_id INTEGER NOT NULL,
            PRIMARY KEY(maintenance_request_id, res_users_id)
        )
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        CREATE INDEX ON maintenance_request_res_users_rel
            (res_users_id, maintenance_request_id)
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO maintenance_request_res_users_rel
            (maintenance_request_id, res_users_id)
        SELECT
            id, user_id
        FROM
            maintenance_request
        WHERE
            user_id IS NOT NULL
        """,
    )


def maintenance_equipment_assign_to(env):
    """
    maintenance.equipment#equipment_assign_to moves from hr_maintenance to
    maintenance. Without hr_maintenance the column does not exist, and with fleet
    the auto installed fleet_maintenance would create it with 'vehicle' on every
    equipment: create it with 'other', the value the existing equipment had
    """
    if (
        openupgrade.is_module_installed(env.cr, "fleet")
        and not openupgrade.is_module_installed(env.cr, "hr_maintenance")
        and not openupgrade.column_exists(
            env.cr, "maintenance_equipment", "equipment_assign_to"
        )
    ):
        openupgrade.add_columns(
            env,
            [("maintenance.equipment", "equipment_assign_to", "selection", "other")],
        )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.add_columns(env, _added_columns)
    maintenance_equipment_assign_to(env)
    maintenance_request_state(env)
    maintenance_request_user_ids(env)

# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_fields = [
    (
        "fleet.vehicle",
        "fleet_vehicle",
        "plan_to_change_car",
        "plan_to_change_vehicle",
    ),
    ("fleet.vehicle.log.services", "fleet_vehicle_log_services", "date", "date_from"),
]

_added_columns = [
    ("fleet.service.type", "company_id", "many2one"),
]


def fleet_vehicle_plan_to_change_vehicle(env):
    """
    Merge fleet.vehicle#plan_to_change_bike into fleet.vehicle#plan_to_change_vehicle
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            fleet_vehicle
        SET
            plan_to_change_vehicle=TRUE
        WHERE
            plan_to_change_bike IS TRUE
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_fields(env, _renamed_fields)
    openupgrade.add_columns(env, _added_columns)
    fleet_vehicle_plan_to_change_vehicle(env)

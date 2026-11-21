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


def fleet_vehicle_unique_license_plate(env):
    """
    Empty license plates become NULL and the repeated ones get the id of the vehicle
    appended, except on the oldest active vehicle, so that the new UNIQUE constraint
    on fleet.vehicle#license_plate can be created. The original plate is kept in a
    legacy column to inform each vehicle in post-migration
    """
    legacy_column = openupgrade.get_legacy_name("license_plate")
    openupgrade.logged_query(
        env.cr,
        f"ALTER TABLE fleet_vehicle ADD COLUMN {legacy_column} VARCHAR",
    )
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE fleet_vehicle
        SET {legacy_column} = license_plate,
            license_plate = NULL
        WHERE license_plate ~ '^\\s*$'
        """,
    )
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE fleet_vehicle
        SET {legacy_column} = fleet_vehicle.license_plate,
            license_plate = concat(
                fleet_vehicle.license_plate, ' (', fleet_vehicle.id, ')'
            )
        FROM (
            SELECT
                id,
                row_number() OVER (
                    PARTITION BY license_plate
                    ORDER BY active DESC NULLS LAST, id
                ) AS position
            FROM fleet_vehicle
            WHERE license_plate IS NOT NULL
        ) AS duplicate
        WHERE duplicate.id = fleet_vehicle.id
            AND duplicate.position > 1
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_fields(env, _renamed_fields)
    openupgrade.add_columns(env, _added_columns)
    fleet_vehicle_plan_to_change_vehicle(env)
    fleet_vehicle_unique_license_plate(env)

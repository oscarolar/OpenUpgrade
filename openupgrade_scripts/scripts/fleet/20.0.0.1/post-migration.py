# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from markupsafe import Markup
from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)


def fleet_vehicle_license_plate_changed(env):
    """
    Inform on each vehicle whose license plate was emptied or made unique in
    pre-migration
    """
    legacy_column = openupgrade.get_legacy_name("license_plate")
    env.cr.execute(
        f"""
        SELECT id, {legacy_column}, license_plate
        FROM fleet_vehicle
        WHERE {legacy_column} IS NOT NULL
        ORDER BY id
        """
    )
    changes = env.cr.fetchall()
    if not changes:
        return
    vehicles = env["fleet.vehicle"].with_context(active_test=False)
    for vehicle_id, old_plate, new_plate in changes:
        vehicles.browse(vehicle_id).message_post(
            body=Markup(
                "<p>The license plate <b>%s</b> was changed to <b>%s</b> during the "
                "migration to Odoo 20, which requires a unique license plate.</p>"
            )
            % (old_plate, new_plate or "(none)"),
            subtype_xmlid="mail.mt_note",
        )
    _logger.warning(
        "License plates changed to satisfy the new UNIQUE(license_plate) of "
        "fleet.vehicle (id: old -> new): %s",
        ", ".join(
            f"{vehicle_id}: {old_plate!r} -> {new_plate!r}"
            for vehicle_id, old_plate, new_plate in changes
        ),
    )


def fleet_vehicle_name(env):
    """
    The name of the vehicles is now 'plate: brand/model'
    """
    vehicles = env["fleet.vehicle"].with_context(active_test=False).search([])
    env.add_to_compute(vehicles._fields["name"], vehicles)
    vehicles.flush_recordset(["name"])


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "fleet", "20.0.0.1/noupdate_changes.xml")
    fleet_vehicle_license_plate_changed(env)
    fleet_vehicle_name(env)

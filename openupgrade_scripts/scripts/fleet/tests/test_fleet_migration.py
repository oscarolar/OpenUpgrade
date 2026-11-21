from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestFleetMigration(TransactionCase):
    def _vehicle(self, description):
        return (
            self.env["fleet.vehicle"]
            .with_context(active_test=False)
            .search([("description", "ilike", description)])
        )

    def test_unique_license_plate(self):
        """
        Test that the repeated and blank license plates are fixed so that the
        constraint exists, and that the vehicles are informed
        """
        self.env.cr.execute(
            """
            SELECT 1 FROM pg_constraint
            WHERE conname = 'fleet_vehicle_unique_license_plate'
            """
        )
        self.assertTrue(self.env.cr.fetchone())
        active = self._vehicle("ou20 active")
        archived = self._vehicle("ou20 archived")
        self.assertEqual(active.license_plate, "OU20-DUP")
        self.assertEqual(archived.license_plate, f"OU20-DUP ({archived.id})")
        self.assertFalse(self._vehicle("ou20 empty").license_plate)
        self.assertFalse(self._vehicle("ou20 spaces").license_plate)
        for description in ("ou20 archived", "ou20 empty", "ou20 spaces"):
            self.assertIn(
                "during the migration to Odoo 20",
                " ".join(self._vehicle(description).message_ids.mapped("body")),
            )
        for description in ("ou20 active", "ou20 unique"):
            self.assertNotIn(
                "during the migration to Odoo 20",
                " ".join(self._vehicle(description).message_ids.mapped("body")),
            )

    def test_name(self):
        """
        Test that the name is recomputed with the v20 format, archived included
        """
        self.assertEqual(
            self._vehicle("ou20 unique").name,
            "OU20-UNIQUE: OpenUpgrade v20 brand/OpenUpgrade v20 model",
        )
        archived = self._vehicle("ou20 archived")
        self.assertEqual(
            archived.name,
            f"OU20-DUP ({archived.id}): OpenUpgrade v20 brand/OpenUpgrade v20 model",
        )

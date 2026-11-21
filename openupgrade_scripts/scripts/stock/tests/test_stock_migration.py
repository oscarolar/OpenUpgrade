from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestStockMigration(TransactionCase):
    def test_product_tracking(self):
        """
        Test that products tracked by quantity have no tracking method
        """
        product = self.env["product.product"].search(
            [("name", "=", "OpenUpgrade v20 stock product")]
        )
        self.assertTrue(product)
        self.assertFalse(product.tracking)
        lot_product = self.env["product.product"].search(
            [("name", "=", "OpenUpgrade v20 stock lot product")]
        )
        self.assertEqual(lot_product.tracking, "lot")

    def test_scrap_done(self):
        """
        Test that validated scraps are scrap moves
        """
        move = self.env["stock.move"].search(
            [("origin", "=", "OpenUpgrade v20 done scrap")]
        )
        self.assertEqual(len(move), 1)
        self.assertTrue(move.is_scrap)
        self.assertEqual(move.state, "done")
        self.assertEqual(move.uom_id, self.env.ref("uom.product_uom_dozen"))
        self.assertEqual(move.quantity_product_uom, 12)
        self.assertEqual(move.scrap_reason_tag_ids.name, "OpenUpgrade v20 scrap tag")
        self.assertEqual(move.scrap_reason_tag_ids.color, 0xFF0000)

    def test_scrap_draft(self):
        """
        Test that draft scraps are draft scrap moves
        """
        move = self.env["stock.move"].search(
            [("origin", "=", "OpenUpgrade v20 draft scrap")]
        )
        self.assertEqual(len(move), 1)
        self.assertTrue(move.is_scrap)
        self.assertEqual(move.state, "draft")
        self.assertEqual(move.quantity, 1)
        self.assertEqual(move.lot_ids.name, "OU20LOT")
        self.assertEqual(move.scrap_reason_tag_ids.name, "OpenUpgrade v20 scrap tag")

    def test_lot_partner_ids(self):
        """
        Test that lots know the partners they were delivered to
        """
        lot = self.env["stock.lot"].search([("name", "=", "OU20LOT")])
        self.assertEqual(lot.partner_ids.name, "OpenUpgrade v20 stock customer")

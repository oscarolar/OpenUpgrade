from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestProductMigration(TransactionCase):
    def test_pricelist_item_compute_price(self):
        """
        Test that only percentage rules become discounts, with the price v19 gave
        """
        pricelist = self.env["product.pricelist"].search(
            [("name", "=", "OpenUpgrade v20 pricelist")]
        )
        items = {int(item.min_quantity): item for item in pricelist.item_ids}
        self.assertEqual(items[1].compute_price, "discount")
        self.assertEqual(items[1].price_discount, 10)
        self.assertEqual(items[1].price_surcharge, 0)
        self.assertEqual(items[2].compute_price, "markup")
        self.assertEqual(items[2].price_discount, 5)
        self.assertEqual(items[3].compute_price, "markup")
        self.assertEqual(items[3].price_discount, -20)

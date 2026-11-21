env = locals().get("env")
company = env.ref("base.main_company")
warehouse = env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
stock_location = warehouse.lot_stock_id
customer_location = env["stock.warehouse"]._get_partner_locations()[0]
product = env["product.product"].create(
    {
        "name": "OpenUpgrade v20 stock product",
        "type": "consu",
        "is_storable": True,
    }
)
lot_product = env["product.product"].create(
    {
        "name": "OpenUpgrade v20 stock lot product",
        "type": "consu",
        "is_storable": True,
        "tracking": "lot",
    }
)
lot = env["stock.lot"].create({"name": "OU20LOT", "product_id": lot_product.id})
env["stock.quant"]._update_available_quantity(product, stock_location, 30)
env["stock.quant"]._update_available_quantity(
    lot_product, stock_location, 5, lot_id=lot
)
tag = env["stock.scrap.reason.tag"].create(
    {"name": "OpenUpgrade v20 scrap tag", "color": "#FF0000"}
)
scrap_done = env["stock.scrap"].create(
    {
        "product_id": product.id,
        "product_uom_id": env.ref("uom.product_uom_dozen").id,
        "scrap_qty": 1,
        "location_id": stock_location.id,
        "origin": "OpenUpgrade v20 done scrap",
        "should_replenish": False,
        "scrap_reason_tag_ids": [(6, 0, tag.ids)],
    }
)
scrap_done.action_validate()
env["stock.scrap"].create(
    {
        "product_id": lot_product.id,
        "lot_id": lot.id,
        "scrap_qty": 1,
        "location_id": stock_location.id,
        "origin": "OpenUpgrade v20 draft scrap",
        "scrap_reason_tag_ids": [(6, 0, tag.ids)],
    }
)
partner = env["res.partner"].create({"name": "OpenUpgrade v20 stock customer"})
picking = env["stock.picking"].create(
    {
        "picking_type_id": warehouse.out_type_id.id,
        "partner_id": partner.id,
        "location_id": stock_location.id,
        "location_dest_id": customer_location.id,
        "move_ids": [
            (
                0,
                0,
                {
                    "product_id": lot_product.id,
                    "product_uom_qty": 2,
                    "product_uom": lot_product.uom_id.id,
                    "location_id": stock_location.id,
                    "location_dest_id": customer_location.id,
                },
            )
        ],
    }
)
picking.action_confirm()
picking.action_assign()
picking.move_ids.picked = True
picking.button_validate()
env.cr.commit()

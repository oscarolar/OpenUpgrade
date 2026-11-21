env = locals().get("env")
pricelist = env["product.pricelist"].create({"name": "OpenUpgrade v20 pricelist"})
env["product.pricelist.item"].create(
    [
        {
            "pricelist_id": pricelist.id,
            "compute_price": "percentage",
            "percent_price": 10,
            "price_surcharge": 5,
            "min_quantity": 1,
        },
        {
            "pricelist_id": pricelist.id,
            "compute_price": "formula",
            "base": "list_price",
            "price_discount": 5,
            "min_quantity": 2,
        },
        {
            "pricelist_id": pricelist.id,
            "compute_price": "formula",
            "base": "standard_price",
            "price_markup": 20,
            "min_quantity": 3,
        },
    ]
)
env.cr.execute(
    """
    UPDATE product_pricelist_item SET price_discount=7
    WHERE pricelist_id=%s AND min_quantity=3
    """,
    (pricelist.id,),
)
env.cr.commit()

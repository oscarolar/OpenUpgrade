env = locals().get("env")
brand = env["fleet.vehicle.model.brand"].create({"name": "OpenUpgrade v20 brand"})
model = env["fleet.vehicle.model"].create(
    {"name": "OpenUpgrade v20 model", "brand_id": brand.id}
)
Vehicle = env["fleet.vehicle"]
archived = Vehicle.create(
    {"model_id": model.id, "license_plate": "OU20-DUP", "description": "ou20 archived"}
)
archived.action_archive()
Vehicle.create(
    {"model_id": model.id, "license_plate": "OU20-DUP", "description": "ou20 active"}
)
Vehicle.create(
    {"model_id": model.id, "license_plate": "OU20-UNIQUE", "description": "ou20 unique"}
)
empty = Vehicle.create({"model_id": model.id, "description": "ou20 empty"})
spaces = Vehicle.create({"model_id": model.id, "description": "ou20 spaces"})
env.cr.execute("UPDATE fleet_vehicle SET license_plate = '' WHERE id = %s", (empty.id,))
env.cr.execute(
    "UPDATE fleet_vehicle SET license_plate = '   ' WHERE id = %s", (spaces.id,)
)
env.cr.commit()

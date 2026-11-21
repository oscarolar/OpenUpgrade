from openupgradelib import openupgrade

_renamed_fields = [
    ("mrp.bom", "mrp_bom", "product_uom_id", "uom_id"),
    ("mrp.bom.byproduct", "mrp_bom_byproduct", "product_uom_id", "uom_id"),
    ("mrp.bom.line", "mrp_bom_line", "product_uom_id", "uom_id"),
    ("mrp.production", "mrp_production", "product_uom_id", "uom_id"),
    (
        "mrp.production",
        "mrp_production",
        "location_final_id",
        "forecasted_location_id",
    ),
    ("mrp.unbuild", "mrp_unbuild", "product_uom_id", "uom_id"),
    ("mrp.workcenter.capacity", "mrp_workcenter_capacity", "product_uom_id", "uom_id"),
]

_added_columns = [
    ("mrp.production", "duration", "float"),
    ("mrp.production", "duration_expected", "float"),
]


def mrp_production_duration(env):
    """
    Precompute the now stored fields mrp.production#duration and
    mrp.production#duration_expected
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE mrp_production
        SET duration = COALESCE(workorder.duration, 0),
            duration_expected = COALESCE(workorder.duration_expected, 0)
        FROM mrp_production self
        LEFT JOIN (
            SELECT
                production_id,
                SUM(duration) AS duration,
                SUM(duration_expected) AS duration_expected
            FROM mrp_workorder
            GROUP BY production_id
        ) workorder ON workorder.production_id = self.id
        WHERE mrp_production.id = self.id
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_fields(env, _renamed_fields)
    openupgrade.add_columns(env, _added_columns)
    mrp_production_duration(env)

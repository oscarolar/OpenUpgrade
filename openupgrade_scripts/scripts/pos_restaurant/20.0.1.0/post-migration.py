from openupgradelib import openupgrade


def restaurant_table_floor_plan_layout(env):
    """
    Position, size, shape and color of a table are stored in
    restaurant.table#floor_plan_layout now
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE restaurant_table
        SET floor_plan_layout = jsonb_strip_nulls(jsonb_build_object(
            'left', round(position_h)::integer,
            'top', round(position_v)::integer,
            'width', round(width)::integer,
            'height', round(height)::integer,
            'color', NULLIF(color, ''),
            'shape', CASE
                WHEN shape = 'round' AND round(width) = round(height) THEN 'circle'
                WHEN shape = 'round' THEN 'oval'
                WHEN round(width) = round(height) THEN 'square'
                ELSE 'rect'
            END
        ))
        WHERE floor_plan_layout IS NULL
        """,
    )


def restaurant_floor_floor_plan_layout(env):
    """
    Background color and image of a floor are stored in
    restaurant.floor#floor_plan_layout now, the image being an attachment of the
    floor without res_field
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE restaurant_floor
        SET floor_plan_layout = jsonb_strip_nulls(jsonb_build_object(
            'bgColor', NULLIF(background_color, ''),
            'bgImage', (
                SELECT jsonb_build_object('id', ir_attachment.id)
                FROM ir_attachment
                WHERE ir_attachment.res_model = 'restaurant.floor'
                AND ir_attachment.res_field = 'floor_background_image'
                AND ir_attachment.res_id = restaurant_floor.id
                ORDER BY ir_attachment.id DESC
                LIMIT 1
            )
        ))
        WHERE floor_plan_layout IS NULL
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_attachment
        SET res_field = NULL
        FROM restaurant_floor
        WHERE ir_attachment.res_model = 'restaurant.floor'
        AND ir_attachment.res_field = 'floor_background_image'
        AND ir_attachment.res_id = restaurant_floor.id
        AND (restaurant_floor.floor_plan_layout->'bgImage'->>'id')::integer
            = ir_attachment.id
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    restaurant_table_floor_plan_layout(env)
    restaurant_floor_floor_plan_layout(env)

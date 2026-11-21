from openupgradelib import openupgrade

_deleted_xmlids = [
    "mrp.mrp_mo_in_cancelled",
    "mrp.mrp_mo_in_confirmed",
    "mrp.mrp_mo_in_done",
    "mrp.mrp_mo_in_progress",
    "mrp.mrp_mo_in_to_close",
]


def mrp_unbuild_lot_ids(env):
    """
    mrp.unbuild#lot_id is the many2many field lot_ids now
    """
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO mrp_unbuild_stock_lot_rel (mrp_unbuild_id, stock_lot_id)
        SELECT id, lot_id
        FROM mrp_unbuild
        WHERE lot_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """,
    )


def stock_move_scrap(env):
    """
    stock.scrap is merged into stock.move. The moves of validated scraps carry the
    link to the manufacturing order since v19, pass it to the draft scrap moves
    created by the migration of stock, that keeps stock_move.scrap_id for this.
    """
    if not openupgrade.column_exists(
        env.cr, "stock_move", "scrap_id"
    ) or not openupgrade.table_exists(env.cr, "stock_scrap"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        WITH scrap AS (
            SELECT
                stock_move.id AS move_id,
                COALESCE(
                    stock_scrap.production_id, mrp_workorder.production_id
                ) AS production_id,
                EXISTS (
                    SELECT 1 FROM stock_move finished
                    WHERE finished.production_id = COALESCE(
                        stock_scrap.production_id, mrp_workorder.production_id
                    )
                    AND finished.product_id = stock_move.product_id
                    AND finished.id != stock_move.id
                    AND finished.is_scrap IS NOT TRUE
                ) AS is_finished
            FROM stock_move
            JOIN stock_scrap ON stock_scrap.id = stock_move.scrap_id
            LEFT JOIN mrp_workorder ON mrp_workorder.id = stock_scrap.workorder_id
            WHERE stock_move.is_scrap
            AND stock_move.production_id IS NULL
            AND stock_move.raw_material_production_id IS NULL
            AND COALESCE(
                stock_scrap.production_id, mrp_workorder.production_id
            ) IS NOT NULL
        )
        UPDATE stock_move
        SET
            production_id = CASE
                WHEN scrap.is_finished THEN scrap.production_id
            END,
            raw_material_production_id = CASE
                WHEN NOT scrap.is_finished THEN scrap.production_id
            END
        FROM scrap
        WHERE stock_move.id = scrap.move_id
        """,
    )


def mail_message_subtype(env):
    """
    The subtypes per state of a manufacturing order are replaced by the single
    subtype mrp.mt_mo_state
    """
    new_subtype = env.ref("mrp.mt_mo_state")
    old_subtype_ids = tuple(
        subtype.id
        for subtype in (
            env.ref(xmlid, raise_if_not_found=False) for xmlid in _deleted_xmlids
        )
        if subtype
    )
    if not old_subtype_ids:
        return
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO mail_followers_mail_message_subtype_rel
            (mail_followers_id, mail_message_subtype_id)
        SELECT DISTINCT mail_followers_id, %s
        FROM mail_followers_mail_message_subtype_rel
        WHERE mail_message_subtype_id IN %s
        ON CONFLICT DO NOTHING
        """,
        (new_subtype.id, old_subtype_ids),
    )
    openupgrade.logged_query(
        env.cr,
        "UPDATE mail_message SET subtype_id = %s WHERE subtype_id IN %s",
        (new_subtype.id, old_subtype_ids),
    )
    openupgrade.delete_records_safely_by_xml_id(env, _deleted_xmlids)


@openupgrade.migrate()
def migrate(env, version):
    mrp_unbuild_lot_ids(env)
    stock_move_scrap(env)
    mail_message_subtype(env)

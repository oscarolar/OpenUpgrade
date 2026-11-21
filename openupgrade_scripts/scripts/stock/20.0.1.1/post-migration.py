# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)

_deleted_xmlids = [
    "stock.seq_picking_wave",
]


def stock_scrap_reason_tag_color(env):
    """
    stock.scrap.reason.tag#color was a hex string and is an integer now
    """
    legacy_column = openupgrade.get_legacy_name("color")
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE stock_scrap_reason_tag
        SET color=('x' || lpad(substr({legacy_column}, 2), 8, '0'))::bit(32)::integer
        WHERE {legacy_column} ~ '^#[0-9a-fA-F]{{6}}$'
        """,
    )


def stock_scrap_done(env):
    """
    stock.scrap is merged into stock.move: flag the moves of existing scraps and
    pass them the data that lived on the scrap
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE stock_move
        SET is_scrap=True, should_replenish_scrapped=stock_scrap.should_replenish
        FROM stock_scrap
        WHERE stock_move.scrap_id=stock_scrap.id
        """,
    )


def stock_scrap_draft(env):
    """
    Scraps that were never validated have no move in v19, create a draft scrap move
    for them. The link is kept in the legacy column stock_move.scrap_id so that
    dependent modules can pass their own data.
    """
    env.cr.execute(
        """
        SELECT
            stock_scrap.id, stock_scrap.name, stock_scrap.origin,
            stock_scrap.company_id, stock_scrap.product_id,
            stock_scrap.product_uom_id, stock_scrap.scrap_qty,
            stock_scrap.location_id, stock_scrap.scrap_location_id,
            stock_scrap.lot_id, stock_scrap.should_replenish,
            stock_picking.id, stock_picking.name
        FROM stock_scrap
        LEFT JOIN stock_picking
            ON stock_picking.id=stock_scrap.picking_id
            AND stock_picking.state NOT IN ('done', 'cancel')
        WHERE stock_scrap.state='draft'
        AND NOT EXISTS (
            SELECT 1 FROM stock_move WHERE stock_move.scrap_id=stock_scrap.id
        )
        ORDER BY stock_scrap.id
        """
    )
    for (
        scrap_id,
        name,
        origin,
        company_id,
        product_id,
        uom_id,
        quantity,
        location_id,
        location_dest_id,
        lot_id,
        should_replenish,
        picking_id,
        picking_name,
    ) in env.cr.fetchall():
        vals = {
            "is_scrap": True,
            "state": "draft",
            "origin": origin or picking_name or name,
            "company_id": company_id,
            "product_id": product_id,
            "uom_id": uom_id,
            "product_uom_qty": quantity,
            "location_id": location_id,
            "location_dest_id": location_dest_id,
            "picking_id": picking_id,
            "should_replenish_scrapped": should_replenish,
        }
        try:
            with env.cr.savepoint():
                move = (
                    env["stock.move"]
                    .with_company(company_id)
                    .with_context(tracking_disable=True)
                    .create(vals)
                )
                move.write(
                    dict(quantity=quantity, **({"lot_ids": [lot_id]} if lot_id else {}))
                )
                env.flush_all()
        except Exception:
            _logger.exception("Draft scrap %s (id %s) not converted", name, scrap_id)
            env.invalidate_all()
            continue
        env.cr.execute(
            "UPDATE stock_move SET scrap_id=%s WHERE id=%s", (scrap_id, move.id)
        )


def stock_scrap_reason_tags(env):
    """
    Pass the reason tags of scraps to their moves
    """
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO stock_move_stock_scrap_reason_tag_rel
            (stock_move_id, stock_scrap_reason_tag_id)
        SELECT stock_move.id, rel.stock_scrap_reason_tag_id
        FROM stock_scrap_stock_scrap_reason_tag_rel rel
        JOIN stock_move ON stock_move.scrap_id=rel.stock_scrap_id
        ON CONFLICT DO NOTHING
        """,
    )


def stock_lot_partner_ids(env):
    """
    stock.lot#partner_ids is stored now and filled when a delivery is validated.
    Fill it with the partners of the done deliveries of every lot.
    """
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO res_partner_stock_lot_rel (stock_lot_id, res_partner_id)
        SELECT DISTINCT stock_move_line.lot_id, stock_picking.partner_id
        FROM stock_move_line
        JOIN stock_move ON stock_move.id=stock_move_line.move_id
        JOIN stock_picking ON stock_picking.id=stock_move.picking_id
        JOIN stock_picking_type
            ON stock_picking_type.id=stock_picking.picking_type_id
        WHERE stock_move_line.state='done'
        AND stock_move_line.lot_id IS NOT NULL
        AND stock_picking.partner_id IS NOT NULL
        AND stock_picking_type.code='outgoing'
        ON CONFLICT DO NOTHING
        """,
    )


def stock_move_line_date(env):
    """
    stock.move.line#date is a stored related to its move's date now
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE stock_move_line
        SET date=stock_move.date
        FROM stock_move
        WHERE stock_move.id=stock_move_line.move_id
        AND stock_move_line.date IS DISTINCT FROM stock_move.date
        """,
    )


def res_company_picking_policy(env):
    """
    The shipping policy was a user default of sale.order#picking_policy and is a
    company setting now
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_company
        SET picking_policy=TRIM(BOTH '"' FROM ir_default.json_value)
        FROM ir_default
        JOIN ir_model_fields ON ir_model_fields.id=ir_default.field_id
        WHERE ir_model_fields.model='sale.order'
        AND ir_model_fields.name='picking_policy'
        AND ir_default.user_id IS NULL
        AND ir_default.condition IS NULL
        AND ir_default.company_id IS NULL
        AND TRIM(BOTH '"' FROM ir_default.json_value) IN ('direct', 'one')
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_company
        SET picking_policy=TRIM(BOTH '"' FROM ir_default.json_value)
        FROM ir_default
        JOIN ir_model_fields ON ir_model_fields.id=ir_default.field_id
        WHERE ir_model_fields.model='sale.order'
        AND ir_model_fields.name='picking_policy'
        AND ir_default.user_id IS NULL
        AND ir_default.condition IS NULL
        AND ir_default.company_id=res_company.id
        AND TRIM(BOTH '"' FROM ir_default.json_value) IN ('direct', 'one')
        """,
    )


def stock_group_stock_picking_batch(env):
    """
    Batch transfers were enabled by installing stock_picking_batch, in v20 they are
    part of stock and enabled with the group stock.group_stock_picking_batch
    """
    if not openupgrade.column_exists(
        env.cr, "stock_picking_batch", openupgrade.get_legacy_name("installed")
    ):
        return
    env.ref("base.group_user").write(
        {"implied_ids": [(4, env.ref("stock.group_stock_picking_batch").id)]}
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "stock", "20.0.1.1/noupdate_changes.xml")
    openupgrade.delete_record_translations(
        env.cr,
        "stock",
        ["mail_template_data_delivery_confirmation"],
        ["body_html"],
    )
    stock_scrap_reason_tag_color(env)
    stock_scrap_done(env)
    stock_scrap_draft(env)
    stock_scrap_reason_tags(env)
    stock_lot_partner_ids(env)
    stock_move_line_date(env)
    res_company_picking_policy(env)
    stock_group_stock_picking_batch(env)
    openupgrade.delete_records_safely_by_xml_id(env, _deleted_xmlids)

# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def repair_order_invoice_ids(env):
    """
    Link the invoices of the sale order of a repair order to the repair order, as
    the compute method of repair.order#invoice_ids does
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            account_move
        SET
            repair_order_id=repair_invoices.repair_order_id
        FROM (
            SELECT DISTINCT ON (account_move_line.move_id)
                account_move_line.move_id, repair_order.id AS repair_order_id
            FROM
                repair_order
            JOIN
                sale_order_line
            ON
                sale_order_line.order_id=repair_order.sale_order_id
            JOIN
                sale_order_line_invoice_rel
            ON
                sale_order_line_invoice_rel.order_line_id=sale_order_line.id
            JOIN
                account_move_line
            ON
                account_move_line.id=sale_order_line_invoice_rel.invoice_line_id
            ORDER BY
                account_move_line.move_id, repair_order.id DESC
        ) repair_invoices
        WHERE
            repair_invoices.move_id=account_move.id
        AND
            account_move.repair_order_id IS NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    repair_order_invoice_ids(env)

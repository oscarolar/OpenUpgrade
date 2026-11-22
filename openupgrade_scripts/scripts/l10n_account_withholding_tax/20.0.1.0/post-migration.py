# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

from odoo.tools import split_every

_invoice_types = (
    "out_invoice",
    "out_refund",
    "out_receipt",
    "in_invoice",
    "in_refund",
    "in_receipt",
)


def _account_payment_withhold(env):
    """
    account.payment#should_withhold_tax becomes the withhold selection: a 19.0
    payment that withheld taxes also paid the net amount
    """
    if not openupgrade.column_exists(env.cr, "account_payment", "should_withhold_tax"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_payment
        SET withhold = 'withhold_pay'
        WHERE should_withhold_tax
            AND withhold IS DISTINCT FROM 'withhold_pay'
        """,
    )


def _account_move_withholding_amounts(env):
    """
    Compute the withholding amounts of the invoices that have withholding taxes
    or are reconciled with entries that withheld taxes; the other moves keep the
    0 set in the pre-migration
    """
    env.cr.execute(
        """
        SELECT aml.move_id
        FROM account_tax tax
        LEFT JOIN account_tax_filiation_rel filiation
            ON filiation.child_tax = tax.id
        JOIN account_move_line_account_tax_rel rel
            ON rel.account_tax_id IN (tax.id, filiation.parent_tax)
        JOIN account_move_line aml ON aml.id = rel.account_move_line_id
        JOIN account_move move ON move.id = aml.move_id
        WHERE tax.is_withholding_tax AND move.move_type IN %(types)s
        UNION
        SELECT term.move_id
        FROM account_tax tax
        JOIN account_move_line wth ON wth.tax_line_id = tax.id
        JOIN account_move_line counterpart ON counterpart.move_id = wth.move_id
        JOIN account_partial_reconcile apr
            ON counterpart.id IN (apr.debit_move_id, apr.credit_move_id)
        JOIN account_move_line term
            ON term.id IN (apr.debit_move_id, apr.credit_move_id)
            AND term.id != counterpart.id
        JOIN account_move move ON move.id = term.move_id
        WHERE tax.is_withholding_tax
            AND term.display_type = 'payment_term'
            AND move.move_type IN %(types)s
        """,
        {"types": _invoice_types},
    )
    move_ids = [move_id for (move_id,) in env.cr.fetchall()]
    AccountMove = env["account.move"]
    fields = [
        AccountMove._fields[name]
        for name in (
            "withholding_total_amount_currency",
            "withholding_deducted_amount_currency",
        )
    ]
    for moves in split_every(1000, move_ids, AccountMove.browse):
        for field in fields:
            env.add_to_compute(field, moves)
        moves.flush_recordset([field.name for field in fields])
        env.invalidate_all()


@openupgrade.migrate()
def migrate(env, version):
    _account_payment_withhold(env)
    _account_move_withholding_amounts(env)

# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

from odoo.tools import split_every


def purchase_order_line_non_deductible_tax(env):
    """
    Compute purchase.order.line#non_deductible_tax for lines with taxes that have
    a non deductible part, without touching the other amounts of the line
    """
    env.cr.execute(
        """
        SELECT DISTINCT
            line_tax.purchase_order_line_id
        FROM
            account_tax_purchase_order_line_rel line_tax
        LEFT JOIN
            account_tax_filiation_rel
        ON
            account_tax_filiation_rel.parent_tax=line_tax.account_tax_id
        JOIN
            account_tax_repartition_line
        ON
            account_tax_repartition_line.tax_id IN (
                line_tax.account_tax_id, account_tax_filiation_rel.child_tax
            )
        WHERE
            account_tax_repartition_line.document_type='invoice'
        AND
            account_tax_repartition_line.repartition_type='tax'
        AND
            account_tax_repartition_line.use_in_tax_closing IS NOT TRUE
        AND
            COALESCE(account_tax_repartition_line.factor_percent, 0) != 0
        """
    )
    line_ids = [line_id for (line_id,) in env.cr.fetchall()]
    AccountTax = env["account.tax"]
    PurchaseOrderLine = env["purchase.order.line"]
    for lines in split_every(1000, line_ids, PurchaseOrderLine.browse):
        for line in lines:
            company = line.company_id or env.company
            base_line = line._prepare_base_line_for_taxes_computation()
            AccountTax._add_tax_details_in_base_line(base_line, company)
            AccountTax._round_base_lines_tax_details([base_line], company)
            non_deductible_tax = sum(
                tax_data["tax_amount_currency"] * tax_data["tax"].non_deductible_amount
                for tax_data in base_line["tax_details"]["taxes_data"]
            )
            if non_deductible_tax:
                env.cr.execute(
                    """
                    UPDATE purchase_order_line SET non_deductible_tax=%s WHERE id=%s
                    """,
                    (non_deductible_tax, line.id),
                )
        lines.invalidate_recordset()


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "purchase", "20.0.1.2/noupdate_changes.xml")
    openupgrade.delete_record_translations(
        env.cr,
        "purchase",
        ["email_template_edi_purchase"],
        ["subject"],
    )
    purchase_order_line_non_deductible_tax(env)

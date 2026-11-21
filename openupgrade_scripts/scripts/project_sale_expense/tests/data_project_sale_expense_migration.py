env = locals().get("env")
company = env.company
plan = env["account.analytic.plan"].create({"name": "OpenUpgrade v20 plan"})
analytic = env["account.analytic.account"].create(
    {"name": "OpenUpgrade v20 analytic", "plan_id": plan.id}
)
product = env["product.product"].create(
    {
        "name": "OpenUpgrade v20 expense product",
        "type": "service",
        "expense_policy": "cost",
        "can_be_expensed": True,
    }
)
partner = env["res.partner"].create({"name": "OpenUpgrade v20 expense customer"})
order = env["sale.order"].create(
    {
        "partner_id": partner.id,
        "order_line": [
            (
                0,
                0,
                {
                    "product_id": product.id,
                    "product_uom_qty": 1,
                    "price_unit": 10,
                    "is_expense": True,
                },
            )
        ],
    }
)
env["account.analytic.line"].create(
    {
        "name": "OpenUpgrade v20 expense revenue",
        "account_id": analytic.id,
        "amount": 10,
        "product_id": product.id,
        "so_line": order.order_line.id,
    }
)
employee = env["hr.employee"].create({"name": "OpenUpgrade v20 expense employee"})
expense = env["hr.expense"].create(
    {
        "name": "OpenUpgrade v20 expense",
        "product_id": product.id,
        "employee_id": employee.id,
        "total_amount_currency": 10,
    }
)
journal = env["account.journal"].search(
    [("type", "=", "general"), ("company_id", "=", company.id)], limit=1
)
accounts = env["account.account"].search(
    [("company_ids", "in", company.id), ("account_type", "=", "expense")], limit=2
)
move = env["account.move"].create(
    {
        "move_type": "entry",
        "journal_id": journal.id,
        "line_ids": [
            (
                0,
                0,
                {
                    "name": "OpenUpgrade v20 expense line",
                    "account_id": accounts[0].id,
                    "debit": 10,
                },
            ),
            (
                0,
                0,
                {
                    "name": "OpenUpgrade v20 expense counterpart",
                    "account_id": accounts[-1].id,
                    "credit": 10,
                },
            ),
        ],
    }
)
move_line = move.line_ids.filtered(lambda line: line.debit)
env.cr.execute(
    "UPDATE account_move_line SET expense_id = %s WHERE id = %s",
    (expense.id, move_line.id),
)
env["account.analytic.line"].create(
    {
        "name": "OpenUpgrade v20 expense cost",
        "account_id": analytic.id,
        "amount": -10,
        "move_line_id": move_line.id,
    }
)
env.cr.commit()

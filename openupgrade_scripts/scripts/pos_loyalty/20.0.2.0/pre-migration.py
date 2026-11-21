from openupgradelib import openupgrade

_renamed_fields = [
    ("pos.order.line", "pos_order_line", "coupon_id", "card_id"),
]


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_fields(env, _renamed_fields)

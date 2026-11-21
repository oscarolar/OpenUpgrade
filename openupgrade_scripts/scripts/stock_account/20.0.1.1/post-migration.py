# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import UTC
from zoneinfo import ZoneInfo

from openupgradelib import openupgrade


def _closing_validation_datetime(env, move_id):
    if not (
        openupgrade.table_exists(env.cr, "mail_tracking_value")
        and openupgrade.column_exists(env.cr, "mail_tracking_value", "field_id")
        and openupgrade.column_exists(
            env.cr, "mail_tracking_value", "mail_message_id"
        )
    ):
        return None
    env.cr.execute(
        """
        SELECT mail_tracking_value.create_date
        FROM mail_tracking_value
        JOIN mail_message
            ON mail_message.id=mail_tracking_value.mail_message_id
        JOIN ir_model_fields
            ON ir_model_fields.id=mail_tracking_value.field_id
        WHERE mail_message.model='account.move'
        AND mail_message.res_id=%s
        AND ir_model_fields.model='account.move'
        AND ir_model_fields.name='state'
        ORDER BY mail_tracking_value.id DESC
        LIMIT 1
        """,
        (move_id,),
    )
    row = env.cr.fetchone()
    return row and row[0]


def account_move_closing_datetime(env):
    """
    v19 kept the ids of the last inventory closing entries of every company in the
    parameter <company id>.stock_valuation_closing_ids and derived the closing moment
    from the entry's last state tracking. v20 flags the entries with
    account.move#inventory_closing and stores the moment in closing_datetime.
    """
    env.cr.execute(
        r"""
        SELECT split_part(key, '.', 1)::integer, value
        FROM ir_config_parameter
        WHERE key ~ '^\d+\.stock_valuation_closing_ids$'
        """
    )
    has_inventory_closing = openupgrade.column_exists(
        env.cr, "account_move", "inventory_closing"
    )
    for company_id, value in env.cr.fetchall():
        company = env["res.company"].browse(company_id).exists()
        move_ids = [int(move_id) for move_id in (value or "").split(",") if move_id]
        if not company or not move_ids:
            continue
        tz = ZoneInfo(company._get_company_tz())
        env.cr.execute(
            "SELECT id, date FROM account_move WHERE id IN %s AND company_id=%s",
            (tuple(move_ids), company_id),
        )
        closing_datetimes = {}
        for move_id, date in env.cr.fetchall():
            closing_datetime = _closing_validation_datetime(env, move_id)
            if (
                not closing_datetime
                or closing_datetime.replace(tzinfo=UTC).astimezone(tz).date() != date
            ):
                closing_datetime = company._to_datetime_upper_bound(date)
            closing_datetimes[move_id] = closing_datetime
            openupgrade.logged_query(
                env.cr,
                "UPDATE account_move SET closing_datetime=%s{} WHERE id=%s".format(
                    ", inventory_closing=True" if has_inventory_closing else ""
                ),
                (closing_datetime, move_id),
            )
        listed_ids = [move_id for move_id in move_ids if move_id in closing_datetimes]
        if listed_ids != sorted(
            listed_ids, key=lambda move_id: (closing_datetimes[move_id], move_id)
        ):
            openupgrade.message(
                env.cr,
                "stock_account",
                "account_move",
                "closing_datetime",
                "The closing entries of company %s are not listed in the order of "
                "their closing dates. v19 took the last listed posted entry as "
                "last closing, v20 takes the posted one with the latest "
                "closing_datetime, ids as listed: %s",
                company_id,
                listed_ids,
            )


@openupgrade.migrate()
def migrate(env, version):
    account_move_closing_datetime(env)

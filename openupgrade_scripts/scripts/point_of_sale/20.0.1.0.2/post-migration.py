from openupgradelib import openupgrade

from odoo.tools import split_every


def pos_config_default_partner_id(env):
    """
    Set the receivable account of the default partner in every company with a
    point of sale, as v20 does when creating a pos.config
    """
    env.cr.execute("SELECT DISTINCT company_id FROM pos_config")
    for (company_id,) in env.cr.fetchall():
        env["pos.config"].with_company(company_id)._get_or_create_default_partner()


def pos_config_preparation_devices(env):
    """
    Preparation printers are shown only if the new flag preparation_devices is set
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE pos_config
        SET preparation_devices = True
        WHERE use_order_printer
        """,
    )


def pos_config_receipt_printer_ids(env):
    """
    The epson receipt printer configured in pos.config#epson_printer_ip is a
    pos.printer record of type receipt in pos.config#receipt_printer_ids now, and
    pos.config#iface_cashdrawer is pos.printer#use_cashdrawer
    """
    env.cr.execute(
        """
        SELECT id, epson_printer_ip, iface_cashdrawer
        FROM pos_config
        WHERE other_devices AND COALESCE(epson_printer_ip, '') != ''
        AND NOT EXISTS (
            SELECT 1 FROM pos_config_receipt_printer_rel rel
            WHERE rel.config_id = pos_config.id
        )
        ORDER BY id
        """
    )
    for config_id, printer_ip, use_cashdrawer in env.cr.fetchall():
        config = env["pos.config"].browse(config_id)
        printer = env["pos.printer"].create(
            {
                "name": config.name,
                "printer_type": "epson_epos",
                "use_type": "receipt",
                "printer_ip": printer_ip,
                "use_cashdrawer": bool(use_cashdrawer),
            }
        )
        env.cr.execute(
            """
            INSERT INTO pos_config_receipt_printer_rel (config_id, printer_id)
            VALUES (%s, %s)
            """,
            (config_id, printer.id),
        )


def pos_session_move_id(env):
    """
    The closing entry of a session was pos.session#move_id and is linked with
    account.move#pos_session_sales_id now
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_move
        SET pos_session_sales_id = pos_session.id
        FROM pos_session
        WHERE pos_session.move_id = account_move.id
        AND account_move.pos_session_sales_id IS NULL
        """,
    )


def pos_session_bank_statement_id(env):
    """
    The cash control of a session (opening and closing balance, cash moves) lived
    on pos.session and is an account.bank.statement now, linked with
    pos.session#bank_statement_id
    """
    env.cr.execute(
        """
        SELECT
            pos_session.id, pos_session.name, pos_session.cash_journal_id,
            COALESCE(pos_session.cash_register_balance_start, 0),
            COALESCE(pos_session.cash_register_balance_end_real, 0),
            ARRAY(
                SELECT account_bank_statement_line.id
                FROM account_bank_statement_line
                JOIN account_move
                    ON account_move.id = account_bank_statement_line.move_id
                WHERE account_bank_statement_line.pos_session_id = pos_session.id
                AND account_bank_statement_line.statement_id IS NULL
                AND account_move.journal_id = pos_session.cash_journal_id
            )
        FROM pos_session
        WHERE pos_session.bank_statement_id IS NULL
        AND pos_session.cash_journal_id IS NOT NULL
        ORDER BY pos_session.id
        """
    )
    rows = [
        row
        for row in env.cr.fetchall()
        if row[5] or row[3] or row[4]
    ]
    Statement = env["account.bank.statement"].with_context(tracking_disable=True)
    for chunk in split_every(500, rows):
        statements = Statement.create(
            [
                {
                    "name": name,
                    "journal_id": journal_id,
                    "balance_start": balance_start,
                    "balance_end_real": balance_end_real,
                    "line_ids": [(6, 0, line_ids)],
                }
                for (
                    _session_id,
                    name,
                    journal_id,
                    balance_start,
                    balance_end_real,
                    line_ids,
                ) in chunk
            ]
        )
        env.flush_all()
        for row, statement in zip(chunk, statements, strict=True):
            env.cr.execute(
                "UPDATE pos_session SET bank_statement_id = %s WHERE id = %s",
                (statement.id, row[0]),
            )
        env.invalidate_all()


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "point_of_sale", "20.0.1.0.2/noupdate_changes.xml")
    pos_config_default_partner_id(env)
    pos_config_preparation_devices(env)
    pos_config_receipt_printer_ids(env)
    pos_session_move_id(env)
    pos_session_bank_statement_id(env)

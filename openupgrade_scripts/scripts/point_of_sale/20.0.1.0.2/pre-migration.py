from openupgradelib import openupgrade

_renamed_fields = [
    ("pos.config", "pos_config", "is_order_printer", "use_order_printer"),
    ("pos.config", "pos_config", "is_header_or_footer", "use_header_or_footer"),
    (
        "pos.config",
        "pos_config",
        "is_closing_entry_by_product",
        "use_closing_entry_by_product",
    ),
    (
        "pos.config",
        "pos_config",
        "auto_validate_terminal_payment",
        "auto_validate_electronic_payment",
    ),
    ("pos.config", "pos_config", "printer_ids", "preparation_printer_ids"),
    ("pos.printer", "pos_printer", "epson_printer_ip", "printer_ip"),
    (
        "pos.payment.method",
        "pos_payment_method",
        "use_payment_terminal",
        "payment_provider",
    ),
    ("pos.payment.method", "pos_payment_method", "image", "custom_image"),
]

_added_columns = [
    ("pos.payment.method", "type", "selection"),
    ("pos.payment", "currency_rate", "float"),
]


def pos_payment_method_type(env):
    """
    pos.payment.method#type was computed from the journal and is a plain stored
    required field now
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE pos_payment_method
        SET type = CASE
            WHEN account_journal.type IN ('cash', 'bank') THEN account_journal.type
            ELSE 'pay_later'
        END
        FROM pos_payment_method self
        LEFT JOIN account_journal ON account_journal.id = self.journal_id
        WHERE pos_payment_method.id = self.id
        """,
    )


def pos_payment_method_payment_method_type(env):
    """
    Selection value qr_code of pos.payment.method#payment_method_type is
    bank_qr_code now
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE pos_payment_method
        SET payment_method_type = 'bank_qr_code'
        WHERE payment_method_type = 'qr_code'
        """,
    )


def pos_payment_method_company_id(env):
    """
    pos.payment.method#company_id is required now
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE pos_payment_method
        SET company_id = COALESCE(
            (
                SELECT account_journal.company_id
                FROM account_journal
                WHERE account_journal.id = pos_payment_method.journal_id
            ),
            (
                SELECT pos_config.company_id
                FROM pos_config_pos_payment_method_rel rel
                JOIN pos_config ON pos_config.id = rel.pos_config_id
                WHERE rel.pos_payment_method_id = pos_payment_method.id
                ORDER BY pos_config.id
                LIMIT 1
            ),
            (SELECT id FROM res_company ORDER BY id LIMIT 1)
        )
        WHERE company_id IS NULL
        """,
    )


def pos_payment_currency_rate(env):
    """
    pos.payment#currency_rate was related to the order and is a plain stored field
    now
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE pos_payment
        SET currency_rate = pos_order.currency_rate
        FROM pos_order
        WHERE pos_order.id = pos_payment.pos_order_id
        """,
    )


def pos_bill_name(env):
    """
    pos.bill#name is required now
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE pos_bill
        SET name = COALESCE(trim(to_char(value, 'FM999999999990.00')), '0')
        WHERE name IS NULL
        """,
    )


def pos_config_journal_id(env):
    """
    In v19 pos.config#journal_id held the session closing entries and
    invoice_journal_id the invoices. In v20 journal_id is the invoice journal and the
    closing entries go to the new closing_journal_id, that the ORM fills with a new
    sale journal with code POSC.
    The v19 journal is kept in a legacy column.
    """
    openupgrade.copy_columns(env.cr, {"pos_config": [("journal_id", None, None)]})
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE pos_config
        SET journal_id = invoice_journal_id
        WHERE invoice_journal_id IS NOT NULL
        """,
    )


def account_journal_poss_code(env):
    """
    v20 searches a sale journal with code POSS per company when closing a session
    and creates it if missing. The v19 journal with this code is of type general, so
    the creation would violate the unique constraint on the journal code.
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_journal
        SET code = 'POSSO'
        WHERE code = 'POSS'
        AND type != 'sale'
        AND NOT EXISTS (
            SELECT 1 FROM account_journal other
            WHERE other.company_id = account_journal.company_id
            AND other.code = 'POSSO'
        )
        """,
    )


def pos_config_default_partner_id(env):
    """
    Create the partner the new required field pos.config#default_partner_id
    defaults to, so that the ORM does not create one without xmlid when it
    initializes the column
    """
    if env.ref(
        "point_of_sale.default_session_closing_partner", raise_if_not_found=False
    ):
        return
    partner = (
        env["res.partner"]
        .with_context(tracking_disable=True)
        .create({"name": "Odoo POS", "is_company": False, "active": False})
    )
    openupgrade.add_xmlid(
        env.cr,
        "point_of_sale",
        "default_session_closing_partner",
        "res.partner",
        partner.id,
        noupdate=True,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_fields(env, _renamed_fields)
    openupgrade.add_columns(env, _added_columns)
    pos_payment_method_type(env)
    pos_payment_method_payment_method_type(env)
    pos_payment_method_company_id(env)
    pos_payment_currency_rate(env)
    pos_bill_name(env)
    pos_config_journal_id(env)
    account_journal_poss_code(env)
    pos_config_default_partner_id(env)

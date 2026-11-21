# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_xmlid_renames = [
    ("payment.cron_post_process_payment_tx", "payment.post_processing_cron"),
]


def _payment_provider_is_live(env):
    """
    payment.provider#state is replaced by is_live: only enabled providers are
    live, and a disabled provider is left as a freshly installed one (not live
    and not published).
    """
    openupgrade.logged_query(
        env.cr, "ALTER TABLE payment_provider ADD COLUMN IF NOT EXISTS is_live bool"
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE payment_provider
        SET is_live = (state = 'enabled'),
            is_published = (is_published AND state <> 'disabled')
        """,
    )


def _copied_columns(env, table, excluded):
    env.cr.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = %s AND column_name <> ALL(%s)
        ORDER BY ordinal_position
        """,
        (table, list(excluded)),
    )
    return [row[0] for row in env.cr.fetchall()]


def _payment_method_provider_id(env):
    """
    A payment method used to be shared by several providers and now belongs to
    one (payment.method#provider_id). Keep the record for its first provider
    and copy it, with its brands, countries, currencies and images, for each
    of the others. Transactions and tokens follow the copy of their provider.
    """
    origin = openupgrade.get_legacy_name("origin_id")
    openupgrade.logged_query(
        env.cr,
        f"""
        ALTER TABLE payment_method
        ADD COLUMN IF NOT EXISTS provider_id int4,
        ADD COLUMN IF NOT EXISTS {origin} int4
        """,
    )
    columns = _copied_columns(
        env,
        "payment_method",
        ("id", "provider_id", origin, "primary_payment_method_id"),
    )
    plain = ", ".join(f'"{column}"' for column in columns)
    prefixed = ", ".join(f'pm."{column}"' for column in columns)
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE payment_method pm
        SET provider_id = sub.provider_id
        FROM (
            SELECT payment_method_id, min(payment_provider_id) AS provider_id
            FROM payment_method_payment_provider_rel
            GROUP BY payment_method_id
        ) sub
        WHERE pm.id = sub.payment_method_id
            AND pm.primary_payment_method_id IS NULL
        """,
    )
    openupgrade.logged_query(
        env.cr,
        f"""
        INSERT INTO payment_method ({plain}, provider_id, {origin})
        SELECT {prefixed}, rel.payment_provider_id, pm.id
        FROM payment_method pm
        JOIN payment_method_payment_provider_rel rel
            ON rel.payment_method_id = pm.id
        WHERE pm.primary_payment_method_id IS NULL
            AND rel.payment_provider_id <> pm.provider_id
        """,
    )
    openupgrade.logged_query(
        env.cr,
        f"""
        INSERT INTO payment_method (
            {plain}, primary_payment_method_id, provider_id, {origin}
        )
        SELECT {prefixed}, primary_copy.id, primary_copy.provider_id, pm.id
        FROM payment_method pm
        JOIN payment_method primary_copy
            ON primary_copy.{origin} = pm.primary_payment_method_id
        WHERE pm.{origin} IS NULL
        """,
    )
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE payment_method pm
        SET provider_id = primary_pm.provider_id
        FROM payment_method primary_pm
        WHERE pm.primary_payment_method_id = primary_pm.id
            AND pm.{origin} IS NULL
            AND primary_pm.{origin} IS NULL
        """,
    )
    for table, column in (
        ("payment_method_res_country_rel", "res_country_id"),
        ("payment_method_res_currency_rel", "res_currency_id"),
    ):
        openupgrade.logged_query(
            env.cr,
            f"""
            INSERT INTO {table} (payment_method_id, {column})
            SELECT pm.id, rel.{column}
            FROM {table} rel
            JOIN payment_method pm ON pm.{origin} = rel.payment_method_id
            """,
        )
    attachment_columns = _copied_columns(env, "ir_attachment", ("id", "res_id"))
    plain = ", ".join(f'"{column}"' for column in attachment_columns)
    prefixed = ", ".join(f'ia."{column}"' for column in attachment_columns)
    openupgrade.logged_query(
        env.cr,
        f"""
        INSERT INTO ir_attachment ({plain}, res_id)
        SELECT {prefixed}, pm.id
        FROM ir_attachment ia
        JOIN payment_method pm ON pm.{origin} = ia.res_id
        WHERE ia.res_model = 'payment.method' AND ia.res_field IS NOT NULL
        """,
    )
    for table in ("payment_transaction", "payment_token"):
        openupgrade.logged_query(
            env.cr,
            f"""
            UPDATE {table} t
            SET payment_method_id = pm.id
            FROM payment_method pm
            WHERE pm.{origin} = t.payment_method_id
                AND pm.provider_id = t.provider_id
            """,
        )


def _payment_method_xmlids(env):
    """
    The payment methods are now data of each provider module, with the same
    name they had in payment: give every method of a standard provider the
    xmlid its module expects, so that the module does not create it again.
    """
    origin = openupgrade.get_legacy_name("origin_id")
    openupgrade.logged_query(
        env.cr,
        f"""
        INSERT INTO ir_model_data (
            module, name, model, res_id, noupdate,
            create_uid, write_uid, create_date, write_date
        )
        SELECT
            imm.name, imd.name, 'payment.method', pm.id, TRUE,
            1, 1, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC'
        FROM payment_method pm
        JOIN ir_model_data imd
            ON imd.model = 'payment.method'
            AND imd.module = 'payment'
            AND imd.res_id = COALESCE(pm.{origin}, pm.id)
        JOIN payment_provider pp ON pp.id = pm.provider_id
        JOIN ir_model_data provider_imd
            ON provider_imd.model = 'payment.provider'
            AND provider_imd.module = 'payment'
            AND provider_imd.res_id = pp.id
        JOIN ir_module_module imm ON imm.id = pp.module_id
        ON CONFLICT DO NOTHING
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_model_data
        SET name = 'payment_method_wero_brand'
        WHERE model = 'payment.method'
            AND name = 'payment_method_wero'
            AND module IN ('payment_adyen', 'payment_mollie', 'payment_stripe')
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        DELETE FROM ir_model_data imd
        USING payment_method pm
        WHERE imd.model = 'payment.method'
            AND imd.module = 'payment'
            AND imd.res_id = pm.id
            AND pm.provider_id IS NOT NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_xmlids(env.cr, _xmlid_renames)
    _payment_provider_is_live(env)
    _payment_method_provider_id(env)
    _payment_method_xmlids(env)

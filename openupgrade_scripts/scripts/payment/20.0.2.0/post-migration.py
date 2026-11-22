# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


_provider_sequences = [
    ("payment_provider_demo", 40, 10),
    ("payment_provider_sepa_direct_debit", 20, 1000),
    ("payment_provider_transfer", 30, 20),
]


def _payment_provider_sequence(env):
    """
    New default display order of some providers: apply it only to the
    providers that keep the default of 19.0, not to the ones reordered by the
    user.
    """
    for name, old_sequence, new_sequence in _provider_sequences:
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE payment_provider pp
            SET sequence = %s
            FROM ir_model_data imd
            WHERE imd.module = 'payment'
                AND imd.name = %s
                AND imd.res_id = pp.id
                AND pp.sequence = %s
            """,
            (new_sequence, name, old_sequence),
        )


def _payment_method_without_provider(env):
    """
    A payment method needs a provider now: remove the ones that had none and
    are not used by any transaction or token, archive the rest.
    """
    openupgrade.logged_query(
        env.cr,
        """
        DELETE FROM payment_method pm
        WHERE pm.provider_id IS NULL
            AND NOT EXISTS (
                SELECT 1 FROM payment_transaction pt
                JOIN payment_method used ON used.id = pt.payment_method_id
                WHERE pm.id IN (used.id, used.primary_payment_method_id)
            )
            AND NOT EXISTS (
                SELECT 1 FROM payment_token pt
                JOIN payment_method used ON used.id = pt.payment_method_id
                WHERE pm.id IN (used.id, used.primary_payment_method_id)
            )
            AND NOT EXISTS (
                SELECT 1 FROM payment_method brand
                WHERE brand.primary_payment_method_id = pm.id
                    AND brand.provider_id IS NOT NULL
            )
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE payment_method SET active = FALSE
        WHERE provider_id IS NULL AND active
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        DELETE FROM ir_model_data imd
        WHERE imd.model = 'payment.method' AND NOT EXISTS (
            SELECT 1 FROM payment_method pm WHERE pm.id = imd.res_id
        )
        """,
    )


_generic_redirect_form_modules = (
    "payment_aps",
    "payment_asiapay",
    "payment_buckaroo",
    "payment_custom",
    "payment_dpo",
    "payment_ecpay",
    "payment_flutterwave",
    "payment_iyzico",
    "payment_mercado_pago",
    "payment_mollie",
    "payment_nuvei",
    "payment_paymob",
    "payment_payu",
    "payment_redsys",
    "payment_worldline",
    "payment_xendit",
)


def _payment_provider_generic_redirect_form(env):
    """
    These provider modules dropped their own redirect form for the generic one
    of payment. Repoint every provider that still uses the old view (also the
    duplicated ones, which the data files do not reach), otherwise the view
    cannot be removed.
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE payment_provider pp
        SET redirect_form_view_id = generic.res_id
        FROM ir_model_data imd, ir_model_data generic
        WHERE imd.model = 'ir.ui.view'
            AND imd.name = 'redirect_form'
            AND imd.module IN %s
            AND imd.res_id = pp.redirect_form_view_id
            AND generic.module = 'payment'
            AND generic.name = 'generic_redirect_form'
        """,
        (_generic_redirect_form_modules,),
    )


@openupgrade.migrate()
def migrate(env, version):
    _payment_provider_sequence(env)
    _payment_method_without_provider(env)
    _payment_provider_generic_redirect_form(env)

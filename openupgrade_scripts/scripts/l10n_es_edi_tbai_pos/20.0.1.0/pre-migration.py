# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _pos_order_l10n_es_invoice_type(env):
    """
    pos.order#l10n_es_tbai_refund_reason is replaced by l10n_es_invoice_type, with
    the same R1-R5 keys
    """
    if not openupgrade.column_exists(env.cr, "pos_order", "l10n_es_tbai_refund_reason"):
        return
    if not openupgrade.column_exists(env.cr, "pos_order", "l10n_es_invoice_type"):
        openupgrade.logged_query(
            env.cr, "ALTER TABLE pos_order ADD COLUMN l10n_es_invoice_type VARCHAR"
        )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE pos_order
        SET l10n_es_invoice_type = l10n_es_tbai_refund_reason
        WHERE l10n_es_invoice_type IS NULL
            AND l10n_es_tbai_refund_reason IS NOT NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _pos_order_l10n_es_invoice_type(env)

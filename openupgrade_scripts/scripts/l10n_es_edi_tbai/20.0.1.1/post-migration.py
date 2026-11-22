# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _account_move_l10n_es_invoice_type(env):
    """
    account.move#l10n_es_tbai_refund_reason is replaced by l10n_es_invoice_type of
    l10n_es, whose R1-R5 keys are the same refund reasons
    """
    if not openupgrade.column_exists(
        env.cr, "account_move", "l10n_es_tbai_refund_reason"
    ):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_move
        SET l10n_es_invoice_type = l10n_es_tbai_refund_reason
        WHERE l10n_es_tbai_refund_reason IN ('R1', 'R2', 'R3', 'R4', 'R5')
            AND move_type IN ('out_refund', 'in_refund')
            AND l10n_es_invoice_type IS DISTINCT FROM l10n_es_tbai_refund_reason
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _account_move_l10n_es_invoice_type(env)

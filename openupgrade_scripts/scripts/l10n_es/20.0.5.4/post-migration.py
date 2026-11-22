# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _account_move_l10n_es_invoice_type(env):
    """
    account.move#l10n_es_is_simplified is replaced by l10n_es_invoice_type:
    F2/R5 are the simplified invoices and refunds, F1/R4 the regular ones. The
    ORM computed the new field from the current data; keep what 19.0 stored
    """
    if not openupgrade.column_exists(env.cr, "account_move", "l10n_es_is_simplified"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_move
        SET l10n_es_invoice_type = CASE
            WHEN move_type IN ('out_refund', 'in_refund') THEN 'R5'
            ELSE 'F2'
        END
        WHERE l10n_es_is_simplified
            AND move_type IN ('out_invoice', 'in_invoice', 'out_refund', 'in_refund')
            AND l10n_es_invoice_type IS DISTINCT FROM CASE
                WHEN move_type IN ('out_refund', 'in_refund') THEN 'R5'
                ELSE 'F2'
            END
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_move
        SET l10n_es_invoice_type = CASE
            WHEN l10n_es_invoice_type = 'R5' THEN 'R4'
            ELSE 'F1'
        END
        WHERE l10n_es_is_simplified IS FALSE
            AND move_type IN ('out_invoice', 'in_invoice', 'out_refund', 'in_refund')
            AND l10n_es_invoice_type IN ('F2', 'R5')
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _account_move_l10n_es_invoice_type(env)

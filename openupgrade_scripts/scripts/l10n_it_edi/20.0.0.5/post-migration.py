# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _l10n_it_document_type_move_types(env):
    """
    l10n_it.document.type#type (sale / purchase) becomes the move_types list.
    The standard types get it from their data file; translate the type of
    the types created by users
    """
    if not openupgrade.column_exists(env.cr, "l10n_it_document_type", "type"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE l10n_it_document_type dt
        SET move_types = CASE dt.type
            WHEN 'sale' THEN '["out_invoice", "out_refund"]'::jsonb
            ELSE '["in_invoice", "in_refund"]'::jsonb
        END
        WHERE dt.type IN ('sale', 'purchase')
            AND dt.move_types IS NULL
            AND NOT EXISTS (
                SELECT 1 FROM ir_model_data imd
                WHERE imd.model = 'l10n_it.document.type'
                    AND imd.res_id = dt.id
            )
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _l10n_it_document_type_move_types(env)

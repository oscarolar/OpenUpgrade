# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _res_partner_invoice_edi_format(env):
    """
    The OIOUBL 2.0.1 format of l10n_dk_oioubl is replaced by OIOUBL 2.1 in
    l10n_dk: move the partners and the defaults that used it
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_partner
        SET invoice_edi_format_store = (
            SELECT jsonb_object_agg(
                key,
                CASE WHEN value = '"oioubl_201"'::jsonb
                    THEN '"oioubl_21"'::jsonb ELSE value END
            )
            FROM jsonb_each(invoice_edi_format_store)
        )
        WHERE jsonb_typeof(invoice_edi_format_store) = 'object'
            AND invoice_edi_format_store @? '$.* ? (@ == "oioubl_201")'
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_default
        SET json_value = '"oioubl_21"'
        FROM ir_model_fields imf
        WHERE imf.id = ir_default.field_id
            AND imf.model = 'res.partner'
            AND imf.name IN ('invoice_edi_format', 'invoice_edi_format_store')
            AND ir_default.json_value = '"oioubl_201"'
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _res_partner_invoice_edi_format(env)

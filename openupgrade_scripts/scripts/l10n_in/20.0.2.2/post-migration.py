# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _res_company_l10n_in_gst_registration_type(env):
    """
    res.company#l10n_in_is_gst_registered becomes the GST registration type:
    19.0 only knew the regular scheme
    """
    if not openupgrade.column_exists(
        env.cr, "res_company", "l10n_in_is_gst_registered"
    ):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_company
        SET l10n_in_gst_registration_type = 'regular'
        WHERE l10n_in_is_gst_registered
            AND l10n_in_gst_registration_type IS NULL
        """,
    )


def _account_tax_tds(env):
    """
    The TDS taxes are now generic withholding taxes: the 19.0 taxes of type
    'tds_sale' / 'tds_purchase' (with no tax use, applied through the
    withholding entry wizard) become 'tds' withholding taxes of the sale /
    purchase use, as the 20.0 chart template defines them
    """
    if not openupgrade.column_exists(env.cr, "account_tax", "is_withholding_tax"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_tax
        SET type_tax_use = CASE l10n_in_tax_type
                WHEN 'tds_sale' THEN 'sale'
                ELSE 'purchase'
            END,
            l10n_in_tax_type = 'tds',
            is_withholding_tax = TRUE
        WHERE l10n_in_tax_type IN ('tds_sale', 'tds_purchase')
        """,
    )


def _l10n_in_pan_entity_tds_certificate_filename(env):
    """
    l10n_in.pan.entity#tds_certificate_filename is removed, keep the name of
    the uploaded file on the attachment of the certificate
    """
    if not openupgrade.column_exists(
        env.cr, "l10n_in_pan_entity", "tds_certificate_filename"
    ):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_attachment
        SET name = pan.tds_certificate_filename
        FROM l10n_in_pan_entity pan
        WHERE ir_attachment.res_model = 'l10n_in.pan.entity'
            AND ir_attachment.res_field = 'tds_certificate'
            AND ir_attachment.res_id = pan.id
            AND COALESCE(pan.tds_certificate_filename, '') <> ''
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _res_company_l10n_in_gst_registration_type(env)
    _account_tax_tds(env)
    _l10n_in_pan_entity_tds_certificate_filename(env)

# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_identification_types = {
    "it_AN": "AR_AN",
    "it_CDI": "AR_CDI",
    "it_CdM": "AR_CDM",
    "it_CIBAR": "AR_CIBAR",
    "it_CPF": "AR_CPF",
    "it_CUIL": "AR_CUIL",
    "it_dni": "AR_DNI",
    "it_ET": "AR_ET",
    "it_LC": "AR_LC",
    "it_LE": "AR_LE",
    "it_Sigd": "AR_SIGD",
    "it_UpApP": "AR_UPAPP",
    "it_CBA": "AR_CI",
    "it_CCat": "AR_CI",
    "it_CCor": "AR_CI",
    "it_CCorr": "AR_CI",
    "it_CICha": "AR_CI",
    "it_CIChu": "AR_CI",
    "it_CIER": "AR_CI",
    "it_CIF": "AR_CI",
    "it_CIJ": "AR_CI",
    "it_CILP": "AR_CI",
    "it_CILR": "AR_CI",
    "it_CIMen": "AR_CI",
    "it_CIMis": "AR_CI",
    "it_CIN": "AR_CI",
    "it_CIRN": "AR_CI",
    "it_CIS": "AR_CI",
    "it_CISC": "AR_CI",
    "it_CISdE": "AR_CI",
    "it_CISF": "AR_CI",
    "it_CISJ": "AR_CI",
    "it_CISL": "AR_CI",
    "it_CIT": "AR_CI",
    "it_CITdF": "AR_CI",
}


def _res_partner_latam_identification(env):
    """
    l10n_latam.identification.type is gone: res.partner#vat only holds the tax
    id. Move the numbers of the other document types of this module to the
    additional identifier that replaces them, before the stored fields that
    read the identifiers are computed.
    """
    if not openupgrade.column_exists(
        env.cr, "res_partner", "l10n_latam_identification_type_id"
    ):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_partner rp
        SET additional_identifiers =
                jsonb_build_object(map.key, rp.vat)
                || COALESCE(rp.additional_identifiers, '{}'::jsonb),
            vat = NULL
        FROM ir_model_data imd
        JOIN unnest(%s::varchar[], %s::varchar[]) AS map(name, key)
            ON map.name = imd.name
        WHERE imd.model = 'l10n_latam.identification.type'
            AND imd.module = %s
            AND imd.res_id = rp.l10n_latam_identification_type_id
            AND COALESCE(rp.vat, '') <> ''
        """,
        (
            list(_identification_types),
            list(_identification_types.values()),
            "l10n_ar",
        ),
    )


@openupgrade.migrate()
def migrate(env, version):
    _res_partner_latam_identification(env)

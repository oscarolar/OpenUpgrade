# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_identification_types = {
    "it_CPP": "PE_CPP",
    "it_DIC": "PE_DIC",
    "it_DNI": "PE_DNI",
    "it_IDCR": "PE_IDCR",
    "it_IN": "PE_IN",
    "it_NDTD": "PE_NDTD",
    "it_PTP": "PE_PTP",
    "it_SP": "PE_SP",
    "it_TAM": "PE_TAM",
    "it_TIN": "PE_TIN",
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
            "l10n_pe",
        ),
    )


@openupgrade.migrate()
def migrate(env, version):
    _res_partner_latam_identification(env)

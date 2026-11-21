# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _res_company_reference_work_entry_type(env):
    """
    res.company#l10n_fr_reference_leave_type pointed to hr.leave.type, which
    hr_holidays turns into hr.work.entry.type: follow the legacy column that
    links both to fill l10n_fr_reference_work_entry_type. hr_holidays may copy
    a time type per country, so the copy of the company's country wins.
    """
    legacy = openupgrade.get_legacy_name("leave_type_id")
    if not openupgrade.column_exists(
        env.cr, "res_company", "l10n_fr_reference_leave_type"
    ) or not openupgrade.column_exists(env.cr, "hr_work_entry_type", legacy):
        return
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE res_company rc
        SET l10n_fr_reference_work_entry_type = (
            SELECT wet.id
            FROM hr_work_entry_type wet
            JOIN res_partner rp ON rp.id = rc.partner_id
            WHERE wet.{legacy} = rc.l10n_fr_reference_leave_type
            ORDER BY wet.country_id IS NOT DISTINCT FROM rp.country_id DESC,
                wet.country_id IS NULL DESC, wet.id
            LIMIT 1
        )
        WHERE rc.l10n_fr_reference_leave_type IS NOT NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _res_company_reference_work_entry_type(env)

# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _hr_work_entry_type_from_leave_type(env):
    """
    The Indian settings of hr.leave.type now live on hr.work.entry.type: copy
    them through the legacy column that hr_holidays leaves on the new records.
    """
    legacy = openupgrade.get_legacy_name("leave_type_id")
    if not openupgrade.column_exists(
        env.cr, "hr_leave_type", "l10n_in_is_sandwich_leave"
    ) or not openupgrade.column_exists(env.cr, "hr_work_entry_type", legacy):
        return
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE hr_work_entry_type wet
        SET l10n_in_is_sandwich_leave = lt.l10n_in_is_sandwich_leave,
            l10n_in_is_limited_to_optional_days =
                lt.l10n_in_is_limited_to_optional_days
        FROM hr_leave_type lt
        WHERE wet.{legacy} = lt.id
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _hr_work_entry_type_from_leave_type(env)

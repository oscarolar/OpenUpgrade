# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def resource_calendar_days_per_week(env):
    """
    Fill resource.calendar#days_per_week for the calendars the ORM doesn't compute it
    for: the average of both weeks for variable ones, and the days implied by the
    hours per week and per day for undefined ones
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE resource_calendar
        SET days_per_week=(
            SELECT COUNT(DISTINCT resource_calendar_attendance.date) / 2.0
            FROM resource_calendar_attendance
            WHERE resource_calendar_attendance.calendar_id=resource_calendar.id
        )
        WHERE calendar_type='variable'
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE resource_calendar
        SET days_per_week=CASE
            WHEN COALESCE(hours_per_day, 0) > 0
            THEN LEAST(7, ROUND((hours_per_week / hours_per_day)::numeric, 5))
            ELSE 0
        END
        WHERE calendar_type='undefined'
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    resource_calendar_days_per_week(env)
    openupgrade.load_data(env, "resource", "20.0.1.1/noupdate_changes.xml")

# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_fields = [
    ("resource.calendar.leaves", "resource_calendar_leaves", "time_type", "count_as"),
]

_added_columns = [
    ("res.company", "tz", "selection"),
    ("resource.calendar", "calendar_type", "selection", "fixed"),
    ("resource.calendar.attendance", "date", "date"),
    ("resource.calendar.attendance", "duration_based", "boolean"),
    ("resource.calendar.attendance", "recurrency", "boolean"),
    ("resource.calendar.attendance", "recurrency_count", "integer", 1),
    ("resource.calendar.attendance", "recurrency_end_type", "selection", "forever"),
    ("resource.calendar.attendance", "recurrency_interval", "integer", 1),
    ("resource.calendar.attendance", "recurrency_type", "selection", "weeks"),
    ("resource.calendar.attendance", "recurrency_until", "date"),
]

_fully_flexible = """
    resource_calendar.calendar_type='undefined'
    AND COALESCE(resource_calendar.hours_per_week, 0)=0
    AND COALESCE(resource_calendar.hours_per_day, 0)=0
    AND resource_calendar.active
"""


def res_company_tz(env):
    """
    Fill res.company#tz, which was related to the partner's timezone, with the
    timezone of the company's calendar, the one v19 used when computing work
    intervals without resource, falling back on the timezone of the partner.
    Companies where both differ are reported
    """
    env.cr.execute(
        """
        SELECT res_company.id, res_company.name, resource_calendar.tz, res_partner.tz
        FROM res_company
        JOIN res_partner ON res_partner.id=res_company.partner_id
        JOIN resource_calendar
        ON resource_calendar.id=res_company.resource_calendar_id
        WHERE resource_calendar.tz IS DISTINCT FROM res_partner.tz
        AND resource_calendar.tz IS NOT NULL
        AND res_partner.tz IS NOT NULL
        ORDER BY res_company.id
        """
    )
    for company_id, name, calendar_tz, partner_tz in env.cr.fetchall():
        openupgrade.message(
            env.cr,
            "resource",
            "res_company",
            "tz",
            "Company %s (id %s) gets the timezone %s of its calendar, the "
            "timezone of its partner is %s",
            name,
            company_id,
            calendar_tz,
            partner_tz,
        )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_company
        SET tz=COALESCE(resource_calendar.tz, res_partner.tz, 'UTC')
        FROM res_company res_company2
        JOIN res_partner
        ON res_partner.id=res_company2.partner_id
        LEFT JOIN resource_calendar
        ON resource_calendar.id=res_company2.resource_calendar_id
        WHERE res_company.id=res_company2.id
        """,
    )


def resource_calendar_calendar_type(env):
    """
    Fill resource.calendar#calendar_type: flexible calendars are undefined, calendars
    in two weeks mode are variable, the rest stays fixed
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE resource_calendar
        SET calendar_type=CASE
            WHEN flexible_hours OR schedule_type='flexible' THEN 'undefined'
            ELSE 'variable'
        END
        WHERE flexible_hours OR schedule_type='flexible' OR two_weeks_calendar
        """,
    )


def resource_calendar_attendance_cleanup(env):
    """
    Delete the attendances v20 doesn't have: breaks (now the gap between two
    attendances), the sections of two weeks calendars, the ones of flexible calendars
    and the ones without duration
    """
    openupgrade.logged_query(
        env.cr,
        """
        DELETE FROM resource_calendar_attendance
        USING resource_calendar
        WHERE
            resource_calendar.id=resource_calendar_attendance.calendar_id
        AND (
            resource_calendar_attendance.day_period='lunch'
            OR resource_calendar_attendance.display_type IS NOT NULL
            OR resource_calendar.calendar_type='undefined'
        )
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE resource_calendar_attendance
        SET duration_hours=hour_to - hour_from
        FROM resource_calendar
        WHERE
            resource_calendar.id=resource_calendar_attendance.calendar_id
        AND resource_calendar.duration_based IS NOT TRUE
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        DELETE FROM resource_calendar_attendance
        WHERE COALESCE(duration_hours, 0) <= 0
        """,
    )


def resource_calendar_attendance_duration_based(env):
    """
    Attendances of duration based calendars had hours centered around 12:00, now a
    duration based attendance is one without hours
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE resource_calendar_attendance
        SET hour_from=0, hour_to=0
        FROM resource_calendar
        WHERE
            resource_calendar.id=resource_calendar_attendance.calendar_id
        AND resource_calendar.duration_based
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE resource_calendar_attendance
        SET duration_based=(hour_from=0 AND hour_to=0)
        """,
    )


def resource_calendar_attendance_two_weeks(env):
    """
    Turn the attendances of two weeks calendars into attendances recurring every two
    weeks. 2000-01-03 is the monday of a week v19 counted as second (week_type 1)
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE resource_calendar_attendance
        SET
            date=DATE '2000-01-03'
                + dayofweek::int
                + CASE WHEN COALESCE(week_type, '0')='1' THEN 0 ELSE 7 END,
            recurrency=TRUE,
            recurrency_interval=2,
            recurrency_until=DATE '9999-12-31'
        FROM resource_calendar
        WHERE
            resource_calendar.id=resource_calendar_attendance.calendar_id
        AND resource_calendar.calendar_type='variable'
        """,
    )


def resource_calendar_leaves_count_as(env):
    """
    Map the values of resource.calendar.leaves#time_type to the ones of count_as
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE resource_calendar_leaves
        SET count_as=CASE count_as
            WHEN 'other' THEN 'working_time'
            ELSE 'absence'
        END
        WHERE count_as IN ('leave', 'other')
        """,
    )


def resource_resource_calendar_id(env):
    """
    A resource without calendar was fully flexible, which now is an undefined calendar
    without hours: assign one per company before the ORM fills the now required
    resource.resource#calendar_id with the calendar of the company
    """
    openupgrade.logged_query(
        env.cr,
        f"""
        INSERT INTO resource_calendar (
            name, active, company_id, calendar_type, schedule_type, flexible_hours,
            tz, hours_per_day, hours_per_week, full_time_required_hours,
            create_uid, write_uid, create_date, write_date
        )
        SELECT
            'Fully Flexible', TRUE, companies.company_id, 'undefined', 'flexible',
            TRUE, 'UTC', 0, 0, 0,
            1, 1, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC'
        FROM (
            SELECT DISTINCT company_id
            FROM resource_resource
            WHERE calendar_id IS NULL
        ) companies
        WHERE NOT EXISTS (
            SELECT 1
            FROM resource_calendar
            WHERE
                resource_calendar.company_id IS NOT DISTINCT FROM companies.company_id
            AND {_fully_flexible}
        )
        """,
    )
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE resource_resource
        SET calendar_id=(
            SELECT MIN(resource_calendar.id)
            FROM resource_calendar
            WHERE
                resource_calendar.company_id
                IS NOT DISTINCT FROM resource_resource.company_id
            AND {_fully_flexible}
        )
        WHERE calendar_id IS NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_fields(env, _renamed_fields)
    openupgrade.add_columns(env, _added_columns)
    res_company_tz(env)
    resource_calendar_calendar_type(env)
    resource_calendar_attendance_cleanup(env)
    resource_calendar_attendance_duration_based(env)
    resource_calendar_attendance_two_weeks(env)
    resource_calendar_leaves_count_as(env)
    resource_resource_calendar_id(env)

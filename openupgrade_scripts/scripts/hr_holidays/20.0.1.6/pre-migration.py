# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_leave_type_column = openupgrade.get_legacy_name("leave_type_id")

_leave_type_references = [
    ("hr_leave", "holiday_status_id"),
    ("hr_leave_allocation", "holiday_status_id"),
    ("hr_leave_accrual_plan", "time_off_type_id"),
]

_renamed_fields = [
    ("hr.leave", "hr_leave", "holiday_status_id", "work_entry_type_id"),
    (
        "hr.leave.allocation",
        "hr_leave_allocation",
        "holiday_status_id",
        "work_entry_type_id",
    ),
    (
        "hr.leave.accrual.plan",
        "hr_leave_accrual_plan",
        "time_off_type_id",
        "work_entry_type_id",
    ),
    (
        "hr.leave.allocation",
        "hr_leave_allocation",
        "number_of_hours_display",
        "number_of_hours",
    ),
    (
        "hr.leave.allocation",
        "hr_leave_allocation",
        "yearly_accrued_amount",
        "yearly_accrued_days",
    ),
    (
        "hr.leave.allocation",
        "hr_leave_allocation",
        "expiring_carryover_days",
        "previous_carryover_number_of_days",
    ),
    (
        "hr.leave.accrual.level",
        "hr_leave_accrual_level",
        "postpone_max_days",
        "max_carriedover_duration",
    ),
]

_model_references = [
    ("ir_model_data", "model"),
    ("ir_attachment", "res_model"),
    ("mail_message", "model"),
    ("mail_activity", "res_model"),
]


def hr_leave_type_country(env):
    """
    Create a temporary table with the country every leave type gets as time type
    and the work entry type it was linked to.

    v20 offers to a company the time types of its country when there is any, and
    the ones without country otherwise. A leave type keeps its country, or takes
    the one of the companies when all of them share it, as long as v20 has time
    types for that country; in any other case it stays without country.
    """
    env.cr.execute(
        """
        SELECT DISTINCT rp.country_id
        FROM res_company rc
        JOIN res_partner rp ON rp.id = rc.partner_id
        WHERE rp.country_id IS NOT NULL
        """
    )
    countries = [country_id for (country_id,) in env.cr.fetchall()]
    country_id = countries[0] if len(countries) == 1 else None
    linked = (
        "lt.work_entry_type_id"
        if openupgrade.column_exists(env.cr, "hr_leave_type", "work_entry_type_id")
        else "NULL::integer"
    )
    openupgrade.logged_query(
        env.cr,
        f"""
        CREATE TEMPORARY TABLE openupgrade_hr_leave_type AS
        SELECT
            lt.id,
            (
                SELECT wet.country_id
                FROM hr_work_entry_type wet
                WHERE wet.country_id = COALESCE(lt.country_id, %(country_id)s)
                LIMIT 1
            ) AS country_id,
            {linked} AS linked_id
        FROM hr_leave_type lt
        """,
        {"country_id": country_id},
    )


def hr_leave_type_to_work_entry_type(env):
    """
    Move the leave types to hr.work.entry.type, recording the id of the leave
    type every time type comes from in a legacy column.

    A leave type takes the work entry type it was linked to, or the one with the
    same code in its country, when no other leave type has taken it; the other
    ones get a new time type.
    """
    openupgrade.logged_query(
        env.cr,
        f"""
        ALTER TABLE hr_work_entry_type
        ADD COLUMN IF NOT EXISTS {_leave_type_column} integer
        """,
    )
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE hr_work_entry_type wet
        SET {_leave_type_column} = ranked.leave_type_id
        FROM (
            SELECT
                candidate.leave_type_id,
                candidate.work_entry_type_id,
                row_number() OVER (
                    PARTITION BY candidate.work_entry_type_id
                    ORDER BY
                        candidate.same_active DESC,
                        candidate.sequence,
                        candidate.leave_type_id
                ) AS position
            FROM (
                SELECT DISTINCT ON (lt.id)
                    lt.id AS leave_type_id,
                    wet.id AS work_entry_type_id,
                    COALESCE(lt.active, FALSE) = COALESCE(wet.active, FALSE)
                        AS same_active,
                    lt.sequence
                FROM openupgrade_hr_leave_type olt
                JOIN hr_leave_type lt ON lt.id = olt.id
                JOIN hr_work_entry_type linked ON linked.id = olt.linked_id
                JOIN hr_work_entry_type wet
                    ON wet.code = linked.code
                    AND wet.country_id IS NOT DISTINCT FROM olt.country_id
                ORDER BY lt.id, wet.id = linked.id DESC, wet.id
            ) candidate
        ) ranked
        WHERE ranked.position = 1 AND wet.id = ranked.work_entry_type_id
        """,
    )
    openupgrade.logged_query(
        env.cr,
        f"""
        INSERT INTO hr_work_entry_type (
            {_leave_type_column}, name, code, country_id, color, sequence, active,
            count_as, resource_calendar_selectable, amount_rate, display_code,
            create_uid, create_date, write_uid, write_date
        )
        SELECT
            lt.id, lt.name, 'LT' || lt.id, olt.country_id, lt.color, lt.sequence,
            lt.active,
            CASE WHEN lt.time_type = 'other' THEN 'working_time' ELSE 'absence' END,
            COALESCE(lt.time_type = 'other', FALSE),
            COALESCE(linked.amount_rate, CASE WHEN lt.unpaid THEN 0 ELSE 1 END),
            linked.display_code,
            lt.create_uid, lt.create_date, lt.write_uid, lt.write_date
        FROM openupgrade_hr_leave_type olt
        JOIN hr_leave_type lt ON lt.id = olt.id
        LEFT JOIN hr_work_entry_type linked ON linked.id = olt.linked_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM hr_work_entry_type wet
            WHERE wet.{_leave_type_column} = lt.id
        )
        ORDER BY lt.id
        """,
    )


def hr_leave_type_references(env):
    """
    Point the many2one fields and the generic references of hr.leave.type to the
    time type of every leave type
    """
    for table, column in _leave_type_references:
        env.cr.execute(
            """
            SELECT c.conname
            FROM pg_constraint c
            JOIN pg_attribute a
                ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
            WHERE c.contype = 'f'
                AND c.conrelid = %s::regclass
                AND a.attname = %s
            """,
            (table, column),
        )
        for (constraint,) in env.cr.fetchall():
            openupgrade.logged_query(
                env.cr, f'ALTER TABLE {table} DROP CONSTRAINT "{constraint}"'
            )
        openupgrade.logged_query(
            env.cr,
            f"""
            UPDATE {table} t
            SET {column} = wet.id
            FROM hr_work_entry_type wet
            WHERE wet.{_leave_type_column} = t.{column}
            """,
        )
    for table, column in _model_references:
        if not openupgrade.table_exists(env.cr, table):
            continue
        res_model_id = ""
        if table == "mail_activity":
            res_model_id = """, res_model_id = (
                SELECT id FROM ir_model WHERE model = 'hr.work.entry.type'
            )"""
        openupgrade.logged_query(
            env.cr,
            f"""
            UPDATE {table} t
            SET {column} = 'hr.work.entry.type', res_id = wet.id{res_model_id}
            FROM hr_work_entry_type wet
            WHERE t.{column} = 'hr.leave.type'
                AND wet.{_leave_type_column} = t.res_id
            """,
        )
    if openupgrade.table_exists(env.cr, "mail_followers"):
        openupgrade.logged_query(
            env.cr,
            f"""
            UPDATE mail_followers mf
            SET res_model = 'hr.work.entry.type', res_id = wet.id
            FROM hr_work_entry_type wet
            WHERE mf.res_model = 'hr.leave.type'
                AND wet.{_leave_type_column} = mf.res_id
                AND NOT EXISTS (
                    SELECT 1
                    FROM mail_followers other
                    WHERE other.res_model = 'hr.work.entry.type'
                        AND other.res_id = wet.id
                        AND other.partner_id = mf.partner_id
                )
            """,
        )


@openupgrade.migrate()
def migrate(env, version):
    hr_leave_type_country(env)
    hr_leave_type_to_work_entry_type(env)
    hr_leave_type_references(env)
    openupgrade.rename_fields(env, _renamed_fields)
    openupgrade.delete_sql_constraint_safely(
        env, "hr_holidays", "hr_leave_allocation", "duration_check"
    )
    openupgrade.delete_sql_constraint_safely(
        env, "hr_holidays", "hr_leave_accrual_level", "valid_postpone_max_days_value"
    )

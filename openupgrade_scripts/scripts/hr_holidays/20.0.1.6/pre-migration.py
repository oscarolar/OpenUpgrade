# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_leave_type_column = openupgrade.get_legacy_name("leave_type_id")
_leave_type_copy_column = openupgrade.get_legacy_name("leave_type_copy")

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
    Create temporary tables with the country every leave type gets as time type,
    the work entry type it was linked to, and the other countries that need
    their own copy of the time type.

    v20 offers to a company the time types of its country when there is any, and
    the ones without country otherwise. So the effective country of a company is
    its country when v20 has time types for it, and none in any other case, also
    for companies without country. A leave type with a country keeps it. One
    without country was offered to all the companies, or to its company: it gets
    the effective country that uses it most and a copy for every other one.
    """
    openupgrade.logged_query(
        env.cr,
        """
        CREATE TEMPORARY TABLE openupgrade_company_country AS
        SELECT
            rc.id AS company_id,
            (
                SELECT wet.country_id
                FROM hr_work_entry_type wet
                WHERE wet.country_id = rp.country_id
                LIMIT 1
            ) AS country_id
        FROM res_company rc
        JOIN res_partner rp ON rp.id = rc.partner_id
        """,
    )
    linked = (
        "lt.work_entry_type_id"
        if openupgrade.column_exists(env.cr, "hr_leave_type", "work_entry_type_id")
        else "NULL::integer"
    )
    openupgrade.logged_query(
        env.cr,
        """
        CREATE TEMPORARY TABLE openupgrade_hr_leave_type_usage AS
        SELECT leave_type_id, country_id, SUM(usage) AS usage
        FROM (
            SELECT
                lt.id AS leave_type_id,
                (
                    SELECT wet.country_id
                    FROM hr_work_entry_type wet
                    WHERE wet.country_id = lt.country_id
                    LIMIT 1
                ) AS country_id,
                0 AS usage
            FROM hr_leave_type lt
            WHERE lt.country_id IS NOT NULL
            UNION ALL
            SELECT lt.id, cc.country_id, 0
            FROM hr_leave_type lt
            JOIN openupgrade_company_country cc
                ON lt.company_id IS NULL OR cc.company_id = lt.company_id
            WHERE lt.country_id IS NULL
            UNION ALL
            SELECT lt.id, cc.country_id, 1
            FROM hr_leave hl
            JOIN hr_leave_type lt ON lt.id = hl.holiday_status_id
            LEFT JOIN hr_employee he ON he.id = hl.employee_id
            JOIN openupgrade_company_country cc
                ON cc.company_id = COALESCE(hl.employee_company_id, he.company_id)
            WHERE lt.country_id IS NULL
            UNION ALL
            SELECT lt.id, cc.country_id, 1
            FROM hr_leave_allocation hla
            JOIN hr_leave_type lt ON lt.id = hla.holiday_status_id
            LEFT JOIN hr_employee he ON he.id = hla.employee_id
            JOIN openupgrade_company_country cc
                ON cc.company_id = COALESCE(hla.employee_company_id, he.company_id)
            WHERE lt.country_id IS NULL
            UNION ALL
            SELECT lt.id, cc.country_id, 1
            FROM hr_leave_accrual_plan hlap
            JOIN hr_leave_type lt ON lt.id = hlap.time_off_type_id
            JOIN openupgrade_company_country cc ON cc.company_id = hlap.company_id
            WHERE lt.country_id IS NULL
        ) leave_type_usage
        GROUP BY leave_type_id, country_id
        """,
    )
    openupgrade.logged_query(
        env.cr,
        f"""
        CREATE TEMPORARY TABLE openupgrade_hr_leave_type AS
        SELECT
            lt.id,
            (
                SELECT usage.country_id
                FROM openupgrade_hr_leave_type_usage usage
                WHERE usage.leave_type_id = lt.id
                ORDER BY usage.usage DESC, usage.country_id NULLS LAST
                LIMIT 1
            ) AS country_id,
            {linked} AS linked_id
        FROM hr_leave_type lt
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        CREATE TEMPORARY TABLE openupgrade_hr_leave_type_copy AS
        SELECT usage.leave_type_id, usage.country_id
        FROM openupgrade_hr_leave_type_usage usage
        JOIN openupgrade_hr_leave_type olt ON olt.id = usage.leave_type_id
        WHERE usage.country_id IS DISTINCT FROM olt.country_id
        """,
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


def hr_work_entry_type_per_country(env):
    """
    Copy the time type of the leave types without country for every other
    effective country that used or could use them, flagged in a legacy column
    """
    openupgrade.logged_query(
        env.cr,
        f"""
        ALTER TABLE hr_work_entry_type
        ADD COLUMN IF NOT EXISTS {_leave_type_copy_column} boolean
        """,
    )
    env.cr.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'hr_work_entry_type' AND column_name != 'id'
        ORDER BY ordinal_position
        """
    )
    columns = [name for (name,) in env.cr.fetchall()]
    values = {
        "country_id": "copy.country_id",
        _leave_type_copy_column: "TRUE",
        "code": f"""CASE
            WHEN EXISTS (
                SELECT 1 FROM hr_work_entry_type other
                WHERE other.code = main.code
                AND other.country_id IS NOT DISTINCT FROM copy.country_id
            ) THEN 'LT' || copy.leave_type_id
            ELSE main.code
        END""",
    }
    openupgrade.logged_query(
        env.cr,
        f"""
        INSERT INTO hr_work_entry_type ({", ".join(columns)})
        SELECT {", ".join(values.get(name, f"main.{name}") for name in columns)}
        FROM openupgrade_hr_leave_type_copy copy
        JOIN hr_work_entry_type main
            ON main.{_leave_type_column} = copy.leave_type_id
        ORDER BY copy.leave_type_id, copy.country_id
        """,
    )


def hr_leave_type_references_per_country(env):
    """
    Point the requests, allocations and accrual plans to the copy of the time type
    for the effective country of the company of the employee
    """
    for table, company in (
        ("hr_leave", "COALESCE(t.employee_company_id, he.company_id)"),
        ("hr_leave_allocation", "COALESCE(t.employee_company_id, he.company_id)"),
        ("hr_leave_accrual_plan", "t.company_id"),
    ):
        employee = (
            ""
            if table == "hr_leave_accrual_plan"
            else "LEFT JOIN hr_employee he ON he.id = t.employee_id"
        )
        openupgrade.logged_query(
            env.cr,
            f"""
            UPDATE {table}
            SET work_entry_type_id = copy.id
            FROM {table} t
            {employee}
            JOIN openupgrade_company_country cc ON cc.company_id = {company}
            JOIN hr_work_entry_type main ON main.id = t.work_entry_type_id
            JOIN hr_work_entry_type copy
                ON copy.{_leave_type_column} = main.{_leave_type_column}
                AND copy.{_leave_type_copy_column}
                AND copy.country_id IS NOT DISTINCT FROM cc.country_id
            WHERE {table}.id = t.id
            AND main.{_leave_type_copy_column} IS NOT TRUE
            AND main.country_id IS DISTINCT FROM cc.country_id
            """,
        )


def hr_leave_type_custom_references(env):
    """
    Point the custom many2one fields, the defaults and the filters of
    hr.leave.type to the time types, and report what can't be converted
    """
    env.cr.execute(
        """
        SELECT imf.id, imf.model, imf.name
        FROM ir_model_fields imf
        WHERE imf.relation = 'hr.leave.type' AND imf.ttype = 'many2one'
        AND imf.store AND imf.state = 'manual'
        """
    )
    for field_id, model, name in env.cr.fetchall():
        table = model.replace(".", "_")
        if not openupgrade.column_exists(env.cr, table, name):
            openupgrade.message(
                env.cr,
                "hr_holidays",
                table,
                name,
                "The custom field %s of %s points to hr.leave.type and could not "
                "be converted to hr.work.entry.type",
                name,
                model,
            )
            continue
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
            (table, name),
        )
        for (constraint,) in env.cr.fetchall():
            openupgrade.logged_query(
                env.cr, f'ALTER TABLE "{table}" DROP CONSTRAINT "{constraint}"'
            )
        openupgrade.logged_query(
            env.cr,
            f"""
            UPDATE "{table}" t
            SET "{name}" = wet.id
            FROM hr_work_entry_type wet
            WHERE wet.{_leave_type_column} = t."{name}"
            AND wet.{_leave_type_copy_column} IS NOT TRUE
            """,
        )
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE ir_model_fields
            SET relation = 'hr.work.entry.type'
            WHERE id = %s
            """,
            (field_id,),
        )
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE ir_default
        SET json_value = wet.id::varchar
        FROM ir_model_fields imf, hr_work_entry_type wet
        WHERE imf.id = ir_default.field_id
        AND imf.ttype = 'many2one'
        AND (
            imf.relation = 'hr.leave.type'
            OR (imf.model, imf.name) IN (
                ('hr.leave', 'holiday_status_id'),
                ('hr.leave.allocation', 'holiday_status_id'),
                ('hr.leave.accrual.plan', 'time_off_type_id')
            )
        )
        AND ir_default.json_value ~ '^[0-9]+$'
        AND wet.{_leave_type_column} = ir_default.json_value::integer
        AND wet.{_leave_type_copy_column} IS NOT TRUE
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_filters
        SET model_id = 'hr.work.entry.type'
        WHERE model_id = 'hr.leave.type'
        """,
    )
    env.cr.execute(
        """
        SELECT id, name, model_id
        FROM ir_filters
        WHERE model_id = 'hr.work.entry.type'
        OR (
            model_id LIKE 'hr.leave%%'
            AND (domain || COALESCE(context, '')) ~
                '(holiday_status_id|time_off_type_id|leave_type)'
        )
        ORDER BY id
        """
    )
    for filter_id, name, model in env.cr.fetchall():
        openupgrade.message(
            env.cr,
            "hr_holidays",
            "ir_filters",
            "domain",
            "The filter %s (id %s) of %s uses leave types, review its domain: "
            "the ids of the time types and the fields of hr.work.entry.type are "
            "not the ones of hr.leave.type",
            name,
            filter_id,
            model,
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
                AND wet.{_leave_type_copy_column} IS NOT TRUE
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
                AND wet.{_leave_type_copy_column} IS NOT TRUE
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
                AND wet.{_leave_type_copy_column} IS NOT TRUE
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
    hr_work_entry_type_per_country(env)
    hr_leave_type_references(env)
    hr_leave_type_custom_references(env)
    openupgrade.rename_fields(env, _renamed_fields)
    hr_leave_type_references_per_country(env)
    openupgrade.delete_sql_constraint_safely(
        env, "hr_holidays", "hr_leave_allocation", "duration_check"
    )
    openupgrade.delete_sql_constraint_safely(
        env, "hr_holidays", "hr_leave_accrual_level", "valid_postpone_max_days_value"
    )

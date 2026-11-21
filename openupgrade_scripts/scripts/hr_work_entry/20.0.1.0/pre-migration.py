# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_xmlids = [
    (
        "hr_work_entry.hr_work_entry_type_out_of_contract",
        "hr_work_entry.generic_hr_work_entry_type_out_of_contract",
    ),
    (
        "hr_work_entry.work_entry_type_attendance",
        "hr_work_entry.generic_work_entry_type_attendance",
    ),
    (
        "hr_work_entry.work_entry_type_compensatory",
        "hr_work_entry.generic_work_entry_type_compensatory",
    ),
    (
        "hr_work_entry.work_entry_type_home_working",
        "hr_work_entry.generic_work_entry_type_home_working",
    ),
    (
        "hr_work_entry.work_entry_type_leave",
        "hr_work_entry.generic_work_entry_type_leave",
    ),
    (
        "hr_work_entry.work_entry_type_legal_leave",
        "hr_work_entry.generic_work_entry_type_legal_leave",
    ),
    (
        "hr_work_entry.work_entry_type_overtime",
        "hr_work_entry.generic_work_entry_type_overtime",
    ),
    (
        "hr_work_entry.work_entry_type_sick_leave",
        "hr_work_entry.generic_work_entry_type_sick_leave",
    ),
    (
        "hr_work_entry.work_entry_type_unpaid_leave",
        "hr_work_entry.generic_work_entry_type_unpaid_leave",
    ),
]

_generic_codes = [
    ("generic_hr_work_entry_type_out_of_contract", "OUT", "000.00"),
    ("generic_work_entry_type_attendance", "WORK100", "002.00"),
    ("generic_work_entry_type_home_working", "WORK110", "002.08"),
    ("generic_work_entry_type_legal_leave", "LEAVE120", "016.00"),
    ("generic_work_entry_type_overtime", "OVERTIME", "040.00"),
    ("generic_work_entry_type_sick_leave", "LEAVE110", "013.00"),
    ("generic_work_entry_type_unpaid_leave", "LEAVE90", "158.00"),
]


def hr_work_entry_type_count_as(env):
    """
    Fill hr.work.entry.type#count_as from the removed boolean is_leave
    """
    openupgrade.add_columns(
        env, [("hr.work.entry.type", "count_as", "selection", "working_time")]
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_work_entry_type
        SET count_as = 'absence'
        WHERE is_leave
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_work_entry_type wet
        SET count_as = 'working_time'
        FROM ir_model_data imd
        WHERE imd.module = 'hr_work_entry'
            AND imd.name = 'generic_work_entry_type_home_working'
            AND imd.model = 'hr.work.entry.type'
            AND imd.res_id = wet.id
        """,
    )


def hr_work_entry_type_generic_codes(env):
    """
    Set the v20 code on the generic work entry types that still have the v19 one,
    the code looks up the attendance, sick and public holiday types by code
    """
    for name, old_code, new_code in _generic_codes:
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE hr_work_entry_type wet
            SET code = %(new_code)s
            FROM ir_model_data imd
            WHERE imd.module = 'hr_work_entry'
                AND imd.name = %(name)s
                AND imd.model = 'hr.work.entry.type'
                AND imd.res_id = wet.id
                AND wet.code = %(old_code)s
                AND NOT EXISTS (
                    SELECT 1
                    FROM hr_work_entry_type other
                    WHERE other.code = %(new_code)s
                        AND other.country_id IS NOT DISTINCT FROM wet.country_id
                )
            """,
            {"name": name, "old_code": old_code, "new_code": new_code},
        )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_xmlids(env.cr, _renamed_xmlids)
    hr_work_entry_type_count_as(env)
    hr_work_entry_type_generic_codes(env)

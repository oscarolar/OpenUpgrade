# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from io import StringIO

from lxml import etree
from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)

_leave_type_column = openupgrade.get_legacy_name("leave_type_id")

_leave_type_fields = [
    "name",
    "color",
    "sequence",
    "create_calendar_meeting",
    "hide_on_dashboard",
    "leave_validation_type",
    "requires_allocation",
    "employee_requests",
    "allocation_validation_type",
    "request_unit",
    "unpaid",
    "include_public_holidays_in_duration",
    "leave_notif_subtype_id",
    "allocation_notif_subtype_id",
    "support_document",
    "allow_request_on_top",
    "elligible_for_accrual_rate",
    "allows_negative",
    "max_allowed_negative",
]


def load_noupdate_changes(env):
    """
    Load noupdate_changes.xml without the time types that come from a leave type,
    those keep the configuration of the leave type
    """
    env.cr.execute(
        f"""
        SELECT imd.module || '.' || imd.name
        FROM ir_model_data imd
        JOIN hr_work_entry_type wet ON wet.id = imd.res_id
        WHERE imd.model = 'hr.work.entry.type'
            AND wet.{_leave_type_column} IS NOT NULL
        """
    )
    xmlids = {xmlid for (xmlid,) in env.cr.fetchall()}
    # pylint: disable=protected-access
    with openupgrade._file_open("hr_holidays", "20.0.1.6/noupdate_changes.xml") as fp:
        root = etree.parse(fp).getroot()
    for node in root.xpath("//record[@model='hr.work.entry.type']"):
        if node.get("id") in xmlids:
            node.getparent().remove(node)
    data = StringIO(etree.tostring(root, encoding="unicode"))
    data.name = None
    openupgrade.convert_xml_import(env, "hr_holidays", data, {}, mode="init")


def hr_work_entry_type_from_leave_type(env):
    """
    Copy the configuration of the leave types to their time types and leave only
    those selectable in Time Off, as in v19
    """
    fields = ", ".join(f"{field} = lt.{field}" for field in _leave_type_fields)
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE hr_work_entry_type wet
        SET {fields},
            active = COALESCE(wet.active, FALSE) OR COALESCE(lt.active, FALSE),
            time_off_selectable = COALESCE(lt.active, FALSE),
            count_as = CASE
                WHEN lt.time_type = 'other' THEN 'working_time' ELSE 'absence'
            END,
            unit_of_measure = CASE
                WHEN lt.request_unit = 'hour' THEN 'hour' ELSE 'day'
            END,
            count_days_as = 'working'
        FROM hr_leave_type lt
        WHERE wet.{_leave_type_column} = lt.id
        """,
    )
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE hr_work_entry_type
        SET time_off_selectable = FALSE,
            requires_allocation = CASE
                WHEN count_as = 'working_time' THEN FALSE ELSE requires_allocation
            END
        WHERE {_leave_type_column} IS NULL
        """,
    )
    env.cr.execute(
        f"""
        SELECT count(*)
        FROM hr_work_entry_type wet
        WHERE wet.{_leave_type_column} IS NOT NULL
            AND wet.country_id IS NULL
            AND EXISTS (
                SELECT 1
                FROM res_company rc
                JOIN res_partner rp ON rp.id = rc.partner_id
                JOIN hr_work_entry_type country_wet
                    ON country_wet.country_id = rp.country_id
            )
        """
    )
    count = env.cr.fetchone()[0]
    if count:
        _logger.warning(
            "%s time types coming from leave types have no country, they are not "
            "selectable by the companies of a country that has its own time types",
            count,
        )


def resource_calendar_leaves_work_entry_type_id(env):
    """
    Set the time type of the leave on its resource.calendar.leaves records
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE resource_calendar_leaves rcl
        SET work_entry_type_id = hl.work_entry_type_id
        FROM hr_leave hl
        WHERE rcl.holiday_id = hl.id
            AND rcl.work_entry_type_id IS DISTINCT FROM hl.work_entry_type_id
        """,
    )


def hr_leave_request_duration(env):
    """
    Fill hr.leave#request_duration from the removed request_unit_half and
    request_unit_hours
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_leave
        SET request_duration = CASE
            WHEN request_unit_hours THEN 'specific'
            ELSE COALESCE(request_date_from_period, 'full')
        END
        WHERE request_unit_hours
            OR (
                request_unit_half
                AND request_date_from = request_date_to
                AND request_date_from_period = request_date_to_period
            )
        """,
    )


def hr_leave_allocation_accrual(env):
    """
    Adapt the accrual fields of the allocations: lastcall was the date of the last
    accrual, now last_accrual, and actual_lastcall the date of the last event, now
    lastcall. Only accrual allocations keep their plan, and the expiration date of
    the carried over days is only kept when there are days to expire.
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_leave_allocation
        SET accrual_plan_id = NULL
        WHERE allocation_type = 'regular' AND accrual_plan_id IS NOT NULL
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_leave_allocation
        SET last_accrual = lastcall,
            lastcall = COALESCE(actual_lastcall, lastcall),
            carried_over_days_expiration_date = CASE
                WHEN COALESCE(previous_carryover_number_of_days, 0) = 0 THEN NULL
                ELSE carried_over_days_expiration_date
            END
        WHERE accrual_plan_id IS NOT NULL
        """,
    )


def group_hr_holidays_employee(env):
    """
    Add the internal users to the new Time Off employee group, which holds the
    access that base.group_user had in v19
    """
    users = (
        env["res.users"]
        .with_context(active_test=False)
        .search([("share", "=", False)])
    )
    env.ref("hr_holidays.group_hr_holidays_employee").write(
        {"user_ids": [(4, user_id) for user_id in users.ids]}
    )


@openupgrade.migrate()
def migrate(env, version):
    load_noupdate_changes(env)
    hr_work_entry_type_from_leave_type(env)
    resource_calendar_leaves_work_entry_type_id(env)
    hr_leave_request_duration(env)
    hr_leave_allocation_accrual(env)
    group_hr_holidays_employee(env)

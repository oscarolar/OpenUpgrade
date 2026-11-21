# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)

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

_codes = [
    (
        "generic_hr_work_entry_type_out_of_contract",
        "OUT",
        "000.00",
    ),
    (
        "generic_work_entry_type_attendance",
        "WORK100",
        "002.00",
    ),
    (
        "generic_work_entry_type_home_working",
        "WORK110",
        "002.08",
    ),
    (
        "generic_work_entry_type_legal_leave",
        "LEAVE120",
        "016.00",
    ),
    (
        "generic_work_entry_type_overtime",
        "OVERTIME",
        "040.00",
    ),
    (
        "generic_work_entry_type_sick_leave",
        "LEAVE110",
        "013.00",
    ),
    (
        "generic_work_entry_type_unpaid_leave",
        "LEAVE90",
        "158.00",
    ),
    (
        "l10n_au_work_entry_type_overtime_pto",
        "l10n_au_overtime_pto",
        "AU.OT.PH",
    ),
    (
        "l10n_au_work_entry_type_overtime_regular",
        "l10n_au_overtime_regular",
        "AU.OT",
    ),
    (
        "l10n_au_work_entry_type_overtime_saturday",
        "l10n_au_overtime_saturday",
        "AU.OT.SAT",
    ),
    (
        "l10n_au_work_entry_type_overtime_saturday_pto",
        "l10n_au_overtime_saturday_pto",
        "AU.OT.PH.SAT",
    ),
    (
        "l10n_au_work_entry_type_overtime_sunday",
        "l10n_au_overtime_sunday",
        "AU.OT.SUN",
    ),
    (
        "l10n_au_work_entry_type_overtime_sunday_pto",
        "l10n_au_overtime_sunday_pto",
        "AU.OT.PH.SUN",
    ),
    (
        "l10n_be_work_entry_type_bank_holiday",
        "LEAVE500",
        "006.00",
    ),
    (
        "l10n_be_work_entry_type_breast_feeding",
        "LEAVE290",
        "146.00",
    ),
    (
        "l10n_be_work_entry_type_credit_time",
        "LEAVE300",
        "147.00",
    ),
    (
        "l10n_be_work_entry_type_economic_unemployment",
        "LEAVE6665",
        "137.00",
    ),
    (
        "l10n_be_work_entry_type_european",
        "LEAVE216",
        "142.20",
    ),
    (
        "l10n_be_work_entry_type_extra_legal",
        "LEAVE213",
        "011.00",
    ),
    (
        "l10n_be_work_entry_type_flemish_training_time_off",
        "LEAVE261",
        "024.04",
    ),
    (
        "l10n_be_work_entry_type_long_sick",
        "LEAVE280",
        "123.00",
    ),
    (
        "l10n_be_work_entry_type_maternity",
        "LEAVE210",
        "128.00",
    ),
    (
        "l10n_be_work_entry_type_medical_assistance",
        "MEDIC01",
        "147.07",
    ),
    (
        "l10n_be_work_entry_type_parental_time_off",
        "LEAVE301",
        "147.05",
    ),
    (
        "l10n_be_work_entry_type_partial_incapacity",
        "LEAVE281",
        "122.04",
    ),
    (
        "l10n_be_work_entry_type_paternity_company",
        "LEAVE220",
        "007.05",
    ),
    (
        "l10n_be_work_entry_type_paternity_legal",
        "LEAVE230",
        "128.05",
    ),
    (
        "l10n_be_work_entry_type_phc",
        "PHC1",
        "006.15",
    ),
    (
        "l10n_be_work_entry_type_recovery_additional",
        "LEAVE295",
        "046.00",
    ),
    (
        "l10n_be_work_entry_type_small_unemployment",
        "LEAVE205",
        "007.00",
    ),
    (
        "l10n_be_work_entry_type_solicitation_time_off",
        "LEAVE600",
        "022.00",
    ),
    (
        "l10n_be_work_entry_type_strike",
        "LEAVE251",
        "132.00",
    ),
    (
        "l10n_be_work_entry_type_training",
        "LEAVE265",
        "020.00",
    ),
    (
        "l10n_be_work_entry_type_training_time_off",
        "LEAVE260",
        "024.00",
    ),
    (
        "l10n_be_work_entry_type_unjustified_reason",
        "LEAVE700",
        "155.00",
    ),
    (
        "l10n_be_work_entry_type_unpredictable",
        "LEAVE250",
        "135.00",
    ),
    (
        "l10n_be_work_entry_type_youth_time_off",
        "YOUNG01",
        "142.99",
    ),
    (
        "l10n_ch_work_entry_type_bank_holiday",
        "CHPUBHOL",
        "006.00",
    ),
    (
        "l10n_hk_work_entry_type_public_holiday",
        "HKLEAVE510",
        "006.00",
    ),
    (
        "l10n_id_work_entry_type_public_holiday",
        "IDLEAVE140",
        "006.00",
    ),
    (
        "uae_public_holiday_entry_type",
        "AEPUBLICH",
        "006.00",
    ),
]

_names = [
    (
        "l10n_au_work_entry_type_overtime_pto",
        "Overtime: Public Time Off",
        "Overtime: Public Holiday",
    ),
    (
        "l10n_au_work_entry_type_overtime_regular",
        "Overtime: Regular",
        "Overtime: Week Day",
    ),
    (
        "l10n_au_work_entry_type_overtime_saturday_pto",
        "Overtime: Saturday & Public Time Off",
        "Overtime: Saturday & Public Holiday",
    ),
    (
        "l10n_au_work_entry_type_overtime_sunday_pto",
        "Overtime: Sunday & Public Time Off",
        "Overtime: Sunday & Public Holiday",
    ),
    (
        "l10n_be_work_entry_type_bank_holiday",
        "Public Holiday",
        "Public holiday",
    ),
    (
        "l10n_be_work_entry_type_breast_feeding",
        "Breastfeeding Break",
        "Breast-feeding leave",
    ),
    (
        "l10n_be_work_entry_type_credit_time",
        "Credit Time",
        "Time credit (with/no motif)",
    ),
    (
        "l10n_be_work_entry_type_economic_unemployment",
        "Economic Unemployment",
        "Economic unemployment",
    ),
    (
        "l10n_be_work_entry_type_extra_legal",
        "Extra Legal Time Off",
        "Extra-legal holiday",
    ),
    (
        "l10n_be_work_entry_type_flemish_training_time_off",
        "Flemish Educational Time Off",
        "Flemish Training Leave (unlimited)",
    ),
    (
        "l10n_be_work_entry_type_long_sick",
        "Long Term Sick",
        "Days of illness after 12 months",
    ),
    (
        "l10n_be_work_entry_type_maternity",
        "Maternity Time Off",
        "Maternity leave",
    ),
    (
        "l10n_be_work_entry_type_medical_assistance",
        "Medical Assistance",
        "Thematic leave - Medical assistance",
    ),
    (
        "l10n_be_work_entry_type_parental_time_off",
        "Parental Time Off",
        "Parental leave",
    ),
    (
        "l10n_be_work_entry_type_partial_incapacity",
        "Partial Incapacity (due to illness)",
        "Reintegration journey < 12 months",
    ),
    (
        "l10n_be_work_entry_type_paternity_company",
        "Paternity Time Off (Paid by Company)",
        "Leave for Birth (days 1-3)",
    ),
    (
        "l10n_be_work_entry_type_paternity_legal",
        "Paternity Time Off (Legal)",
        "Leave for birth (days 4-20)",
    ),
    (
        "l10n_be_work_entry_type_phc",
        "Public Holiday Compensation",
        "Replacement public holiday",
    ),
    (
        "l10n_be_work_entry_type_recovery_additional",
        "Recovery Additional Time",
        "Recovered overtime",
    ),
    (
        "l10n_be_work_entry_type_small_unemployment",
        "Small Unemployment (Brief Holiday)",
        "Circumstancial leave",
    ),
    (
        "l10n_be_work_entry_type_solicitation_time_off",
        "Solicitation Time Off",
        "Absence during notice",
    ),
    (
        "l10n_be_work_entry_type_strike",
        "Strike",
        "Strike recognized by trade union Or Lock-out",
    ),
    (
        "l10n_be_work_entry_type_training",
        "Training",
        "Non-productive absence",
    ),
    (
        "l10n_be_work_entry_type_training_time_off",
        "Educational Time Off",
        "Educational leave (unlimited)",
    ),
    (
        "l10n_be_work_entry_type_unjustified_reason",
        "Unjustified Reason",
        "Illegitimate absence",
    ),
    (
        "l10n_be_work_entry_type_unpredictable",
        "Unpredictable Reason",
        "Imperative family reason (days 1-10/year)",
    ),
    (
        "l10n_be_work_entry_type_youth_time_off",
        "Youth Time Off",
        "Holiday junior worker",
    ),
    (
        "l10n_ch_work_entry_type_bank_holiday",
        "Public Holiday",
        "Public holiday",
    ),
    (
        "l10n_hk_work_entry_type_public_holiday",
        "Public Holiday",
        "Public holiday",
    ),
    (
        "l10n_id_work_entry_type_public_holiday",
        "Public Holiday",
        "Public holiday",
    ),
    (
        "l10n_sa_work_entry_type_sick_leave_0",
        "Sick Leave (Unpaid)",
        "Sick Time Off (Unpaid)",
    ),
    (
        "l10n_sa_work_entry_type_sick_leave_75",
        "Sick Leave (75% Paid)",
        "Sick Time Off 75%",
    ),
    (
        "l10n_us_work_entry_type_double",
        "Double Time Hours",
        "Double Time (2x)",
    ),
    (
        "l10n_us_work_entry_type_overtime",
        "Overtime Hours (Paid at 150%)",
        "Overtime (1.5x)",
    ),
    (
        "uae_public_holiday_entry_type",
        "Public Holiday",
        "Public holiday",
    ),
]

_amount_rates = [
    (
        "generic_hr_work_entry_type_out_of_contract",
        1.0,
        0.0,
    ),
    (
        "generic_work_entry_type_unpaid_leave",
        1.0,
        0.0,
    ),
    (
        "l10n_be_work_entry_type_breast_feeding",
        1.0,
        0.0,
    ),
    (
        "l10n_be_work_entry_type_credit_time",
        1.0,
        0.0,
    ),
    (
        "l10n_be_work_entry_type_economic_unemployment",
        1.0,
        0.0,
    ),
    (
        "l10n_be_work_entry_type_long_sick",
        1.0,
        0.0,
    ),
    (
        "l10n_be_work_entry_type_maternity",
        1.0,
        0.0,
    ),
    (
        "l10n_be_work_entry_type_medical_assistance",
        1.0,
        0.0,
    ),
    (
        "l10n_be_work_entry_type_parental_time_off",
        1.0,
        0.0,
    ),
    (
        "l10n_be_work_entry_type_partial_incapacity",
        1.0,
        0.0,
    ),
    (
        "l10n_be_work_entry_type_paternity_legal",
        1.0,
        0.0,
    ),
    (
        "l10n_be_work_entry_type_strike",
        1.0,
        0.0,
    ),
    (
        "l10n_be_work_entry_type_unjustified_reason",
        1.0,
        0.0,
    ),
    (
        "l10n_be_work_entry_type_unpredictable",
        1.0,
        0.0,
    ),
    (
        "l10n_be_work_entry_type_youth_time_off",
        1.0,
        0.0,
    ),
    (
        "l10n_ch_swissdec_unpaid_wt",
        1.0,
        0.0,
    ),
    (
        "l10n_eg_work_entry_type_sick_leave_75",
        1.0,
        0.75,
    ),
    (
        "l10n_eg_work_entry_type_sick_leave_unpaid",
        1.0,
        0.0,
    ),
    (
        "l10n_lu_work_entry_type_situational_unemployment",
        1.0,
        0.0,
    ),
    (
        "l10n_mx_work_entry_type_care_children_with_cancer_imss",
        1.0,
        0.0,
    ),
    (
        "l10n_mx_work_entry_type_disability_due_to_illness_imss",
        1.0,
        0.0,
    ),
    (
        "l10n_mx_work_entry_type_maternity_imss",
        1.0,
        0.0,
    ),
    (
        "l10n_mx_work_entry_type_work_risk_imss",
        1.0,
        0.0,
    ),
]

_count_as_absence = [
    "l10n_au_work_entry_type_compensation",
    "l10n_au_work_entry_type_defence",
    "l10n_au_work_entry_type_parental",
    "uae_public_holiday_entry_type",
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


def _values(env, rows):
    values = ", ".join(env.cr.mogrify("(%s, %s, %s)", row).decode() for row in rows)
    return values.replace("%", "%%")


def hr_work_entry_type_codes(env):
    """
    Set the v20 code on the work entry types that still have the v19 one, unless
    another type of the same country already uses it: the code looks up the
    attendance, sick and public holiday types by code
    """
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE hr_work_entry_type wet
        SET code = v.new_code
        FROM (VALUES {_values(env, _codes)}) AS v(name, old_code, new_code)
        JOIN ir_model_data imd
            ON imd.module = 'hr_work_entry'
            AND imd.name = v.name
            AND imd.model = 'hr.work.entry.type'
        WHERE imd.res_id = wet.id
            AND wet.code = v.old_code
            AND NOT EXISTS (
                SELECT 1
                FROM hr_work_entry_type other
                WHERE other.code = v.new_code
                    AND other.country_id IS NOT DISTINCT FROM wet.country_id
            )
        RETURNING v.name, v.old_code, v.new_code
        """,
    )
    for name, old_code, new_code in sorted(env.cr.fetchall()):
        _logger.warning(
            "hr.work.entry.type hr_work_entry.%s: code %s changed to %s, update the "
            "salary rules, exports and integrations that use the old code",
            name,
            old_code,
            new_code,
        )


def hr_work_entry_type_names(env):
    """
    Set the v20 name on the work entry types that still have the v19 one
    """
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE hr_work_entry_type wet
        SET name = jsonb_build_object('en_US', v.new_name)
        FROM (VALUES {_values(env, _names)}) AS v(name, old_name, new_name)
        JOIN ir_model_data imd
            ON imd.module = 'hr_work_entry'
            AND imd.name = v.name
            AND imd.model = 'hr.work.entry.type'
        WHERE imd.res_id = wet.id
            AND wet.name->>'en_US' = v.old_name
        """,
    )


def hr_work_entry_type_amount_rates(env):
    """
    Set the v20 rate on the work entry types that still have the v19 one
    """
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE hr_work_entry_type wet
        SET amount_rate = v.new_rate
        FROM (VALUES {_values(env, _amount_rates)}) AS v(name, old_rate, new_rate)
        JOIN ir_model_data imd
            ON imd.module = 'hr_work_entry'
            AND imd.name = v.name
            AND imd.model = 'hr.work.entry.type'
        WHERE imd.res_id = wet.id
            AND wet.amount_rate = v.old_rate
        """,
    )


def hr_work_entry_type_count_as_absence(env):
    """
    The types that v20 turns into absences without being time off types in v19
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_work_entry_type wet
        SET count_as = 'absence'
        FROM ir_model_data imd
        WHERE imd.module = 'hr_work_entry'
            AND imd.name IN %(names)s
            AND imd.model = 'hr.work.entry.type'
            AND imd.res_id = wet.id
            AND wet.is_leave IS NOT TRUE
        """,
        {"names": tuple(_count_as_absence)},
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_xmlids(env.cr, _renamed_xmlids)
    hr_work_entry_type_count_as(env)
    hr_work_entry_type_count_as_absence(env)
    hr_work_entry_type_codes(env)
    hr_work_entry_type_names(env)
    hr_work_entry_type_amount_rates(env)

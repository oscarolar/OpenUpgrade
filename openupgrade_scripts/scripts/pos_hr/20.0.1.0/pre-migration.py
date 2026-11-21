from openupgradelib import openupgrade

_renamed_tables = [
    ("pos_hr_minimal_employee_hr_employee", "pos_hr_restrictive_employee_hr_employee"),
    ("pos_hr_basic_employee_hr_employee", "pos_hr_cashier_employee_hr_employee"),
    ("pos_hr_advanced_employee_hr_employee", "pos_hr_manager_employee_hr_employee"),
]

_renamed_fields = [
    ("pos.config", "pos_config", "minimal_employee_ids", "restrictive_employee_ids"),
    ("pos.config", "pos_config", "basic_employee_ids", "cashier_employee_ids"),
    ("pos.config", "pos_config", "advanced_employee_ids", "manager_employee_ids"),
]


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_tables(env.cr, _renamed_tables)
    openupgrade.rename_fields(env, _renamed_fields)

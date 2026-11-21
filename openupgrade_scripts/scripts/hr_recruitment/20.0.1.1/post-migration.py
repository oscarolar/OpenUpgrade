# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def hr_job_favorite_recruiter_ids(env):
    """
    Fill hr.job#favorite_recruiter_ids (hr.employee) with the employees of the
    users in hr.job#favorite_user_ids
    """
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO job_favorite_recruiter_rel (job_id, recruiter_id)
        SELECT DISTINCT job_favorite_user_rel.job_id, hr_employee.id
        FROM job_favorite_user_rel
        JOIN hr_employee ON hr_employee.user_id = job_favorite_user_rel.user_id
        ON CONFLICT DO NOTHING
        """,
    )


def res_company_applicant_properties_definition(env):
    """
    Applicant properties are defined per company instead of per job: merge the
    definitions of the jobs of every company, and of the jobs of its applicants,
    into res.company#applicant_properties_definition
    """
    openupgrade.logged_query(
        env.cr,
        """
        WITH job_companies AS (
            SELECT id AS job_id, company_id
            FROM hr_job
            WHERE
                company_id IS NOT NULL
                AND applicant_properties_definition IS NOT NULL
            UNION
            SELECT job_id, company_id
            FROM hr_applicant
            WHERE
                job_id IS NOT NULL
                AND company_id IS NOT NULL
                AND applicant_properties IS NOT NULL
        ),
        definitions AS (
            SELECT DISTINCT ON (job_companies.company_id, definition.value->>'name')
                job_companies.company_id,
                hr_job.id AS job_id,
                definition.position,
                definition.value
            FROM job_companies
            JOIN hr_job ON hr_job.id = job_companies.job_id
            CROSS JOIN LATERAL jsonb_array_elements(
                CASE
                    WHEN jsonb_typeof(hr_job.applicant_properties_definition) = 'array'
                    THEN hr_job.applicant_properties_definition
                    ELSE '[]'::jsonb
                END
            ) WITH ORDINALITY AS definition(value, position)
            ORDER BY
                job_companies.company_id, definition.value->>'name', hr_job.id
        )
        UPDATE res_company
        SET applicant_properties_definition = company_definitions.definition
        FROM (
            SELECT
                company_id,
                jsonb_agg(value ORDER BY job_id, position) AS definition
            FROM definitions
            GROUP BY company_id
        ) AS company_definitions
        WHERE company_definitions.company_id = res_company.id
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "hr_recruitment", "20.0.1.1/noupdate_changes.xml")
    openupgrade.delete_record_translations(
        env.cr,
        "hr_recruitment",
        [
            "email_template_data_applicant_congratulations",
            "email_template_data_applicant_interest",
            "email_template_data_applicant_not_interested",
            "email_template_data_applicant_refuse",
        ],
        ["body_html"],
    )
    hr_job_favorite_recruiter_ids(env)
    res_company_applicant_properties_definition(env)

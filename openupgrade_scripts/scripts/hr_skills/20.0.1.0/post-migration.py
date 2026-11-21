# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def mail_activity_type_upload_certification(env):
    """
    Certification activities are scheduled with mail's upload document type:
    move what references the removed certification type there and delete it
    """
    old_type = env.ref(
        "hr_skills.mail_activity_data_upload_certification", raise_if_not_found=False
    )
    new_type = env.ref(
        "mail.mail_activity_data_upload_document", raise_if_not_found=False
    )
    if not old_type:
        return
    if new_type:
        for table, column in (
            ("mail_activity", "activity_type_id"),
            ("mail_message", "mail_activity_type_id"),
            ("mail_activity_plan_template", "activity_type_id"),
            ("ir_act_server", "activity_type_id"),
            ("mail_activity_type", "triggered_next_type_id"),
        ):
            openupgrade.logged_query(
                env.cr,
                f"""
                UPDATE {table}
                SET {column} = %(new_type)s
                WHERE {column} = %(old_type)s
                """,
                {"old_type": old_type.id, "new_type": new_type.id},
            )
    openupgrade.delete_records_safely_by_xml_id(
        env, ["hr_skills.mail_activity_data_upload_certification"]
    )


def hr_resume_line_certificate_filename(env):
    """
    hr.resume.line#certificate_filename is removed, keep the name of the uploaded
    file on the attachment of hr.resume.line#certificate_file
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_attachment
        SET name = hr_resume_line.certificate_filename
        FROM hr_resume_line
        WHERE ir_attachment.res_model = 'hr.resume.line'
            AND ir_attachment.res_field = 'certificate_file'
            AND ir_attachment.res_id = hr_resume_line.id
            AND COALESCE(hr_resume_line.certificate_filename, '') <> ''
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    mail_activity_type_upload_certification(env)
    hr_resume_line_certificate_filename(env)

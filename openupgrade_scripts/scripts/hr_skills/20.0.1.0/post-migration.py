# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def mail_activity_type_upload_certification(env):
    """
    Certification activities are scheduled with mail's upload document type:
    move the activities of the removed certification type there and delete it
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
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE mail_activity
            SET activity_type_id = %(new_type)s
            WHERE activity_type_id = %(old_type)s
            """,
            {"old_type": old_type.id, "new_type": new_type.id},
        )
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE mail_message
            SET mail_activity_type_id = %(new_type)s
            WHERE mail_activity_type_id = %(old_type)s
            """,
            {"old_type": old_type.id, "new_type": new_type.id},
        )
    openupgrade.delete_records_safely_by_xml_id(
        env, ["hr_skills.mail_activity_data_upload_certification"]
    )


@openupgrade.migrate()
def migrate(env, version):
    mail_activity_type_upload_certification(env)

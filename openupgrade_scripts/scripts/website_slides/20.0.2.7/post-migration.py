# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "website_slides", "20.0.2.7/noupdate_changes.xml")
    openupgrade.delete_records_safely_by_xml_id(
        env, ["website_slides.mail_notification_channel_invite"]
    )

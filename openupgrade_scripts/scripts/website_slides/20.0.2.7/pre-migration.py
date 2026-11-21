# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_fields = [
    ("slide.slide", "slide_slide", "date_published", "published_date"),
]

_added_columns = [
    ("slide.channel.partner", "completion_date", "datetime"),
]


def slide_channel_partner_completion_date(env):
    """
    Fill slide.channel.partner#completion_date for attendees who finished the
    course with the date of their last completed content
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            slide_channel_partner
        SET
            completion_date=COALESCE(
                (
                    SELECT MAX(slide_slide_partner.write_date)
                    FROM slide_slide_partner
                    WHERE
                        slide_slide_partner.channel_id=slide_channel_partner.channel_id
                    AND
                        slide_slide_partner.partner_id=slide_channel_partner.partner_id
                    AND
                        slide_slide_partner.completed
                ),
                slide_channel_partner.write_date
            )
        WHERE
            member_status='completed'
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    if openupgrade.column_exists(env.cr, "slide_slide", "date_published"):
        openupgrade.rename_fields(env, _renamed_fields)
    openupgrade.add_columns(env, _added_columns)
    slide_channel_partner_completion_date(env)

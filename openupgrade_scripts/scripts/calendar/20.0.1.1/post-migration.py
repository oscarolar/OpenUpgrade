# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

from odoo.tools import split_every


def calendar_calendar_primary(env):
    """
    Create the primary calendar of internal users and of the users owning events, as
    the post_init_hook does on install, with the default privacy they had in their
    settings
    """
    env.cr.execute(
        """
        SELECT id FROM res_users
        WHERE
            share IS NOT TRUE
            OR id IN (SELECT user_id FROM calendar_event WHERE user_id IS NOT NULL)
        ORDER BY id
        """
    )
    user_ids = [user_id for (user_id,) in env.cr.fetchall()]
    for chunk in split_every(1000, user_ids):
        env["res.users"].browse(chunk)._generate_primary_calendar()
    env.flush_all()
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE calendar_calendar
        SET calendar_default_privacy=res_users_settings.calendar_default_privacy
        FROM calendar_user
        JOIN res_users_settings
        ON res_users_settings.user_id=calendar_user.user_id
        WHERE
            calendar_user.calendar_id=calendar_calendar.id
        AND calendar_user.is_primary
        AND calendar_user.access_role='owner'
        AND res_users_settings.calendar_default_privacy
            IN ('public', 'private', 'confidential')
        """,
    )
    env.invalidate_all()


def calendar_event_calendar_id(env):
    """
    Fill calendar.event#calendar_id with the primary calendar of the user of the event
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE calendar_event
        SET calendar_id=calendar_user.calendar_id
        FROM calendar_user
        WHERE
            calendar_user.user_id=calendar_event.user_id
        AND calendar_user.is_primary
        AND calendar_user.access_role='owner'
        AND calendar_event.calendar_id IS NULL
        """,
    )


def calendar_filters_active(env):
    """
    Unchecked attendee filters are now inactive ones
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE calendar_filters
        SET active=FALSE
        WHERE active AND partner_checked IS FALSE
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    calendar_calendar_primary(env)
    calendar_event_calendar_id(env)
    calendar_filters_active(env)
    openupgrade.load_data(env, "calendar", "20.0.1.1/noupdate_changes.xml")
    openupgrade.delete_record_translations(
        env.cr,
        "calendar",
        [
            "calendar_template_delete_event",
            "calendar_template_meeting_changedate",
            "calendar_template_meeting_invitation",
            "calendar_template_meeting_reminder",
            "calendar_template_meeting_update",
        ],
    )

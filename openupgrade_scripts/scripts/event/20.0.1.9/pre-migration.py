# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_added_columns = [
    ("event.registration", "event_begin_date", "datetime"),
]


def event_registration_event_begin_date(env):
    """
    Fill the now stored event_begin_date from the slot or the event
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE event_registration er
        SET event_begin_date = COALESCE(
            (
                SELECT es.start_datetime
                FROM event_slot es
                WHERE es.id = er.event_slot_id
            ),
            ee.date_begin
        )
        FROM event_event ee
        WHERE ee.id = er.event_id
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.add_columns(env, _added_columns)
    event_registration_event_begin_date(env)

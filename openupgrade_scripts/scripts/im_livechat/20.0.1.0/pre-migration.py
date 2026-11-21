# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_added_columns = [
    ("discuss.channel", "livechat_looking_for_help_since_dt", "datetime"),
    ("im_livechat.channel.member.history", "rating", "selection"),
]


def discuss_channel_livechat_status(env):
    """
    The status 'waiting' (for customer) is gone, those conversations are in progress
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE discuss_channel
        SET livechat_status='in_progress'
        WHERE livechat_status='waiting'
        """,
    )


def discuss_channel_livechat_looking_for_help_since_dt(env):
    """
    Conversations looking for help need the date they started to do so
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE discuss_channel
        SET livechat_looking_for_help_since_dt=COALESCE(
            write_date, create_date, now() AT TIME ZONE 'UTC'
        )
        WHERE livechat_status='need_help'
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    discuss_channel_livechat_status(env)
    openupgrade.add_columns(env, _added_columns)
    discuss_channel_livechat_looking_for_help_since_dt(env)

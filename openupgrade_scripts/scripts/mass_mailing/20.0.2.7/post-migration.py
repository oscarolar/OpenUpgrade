# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

from odoo import tools


def mailing_contact_last_datetimes(env):
    """
    Fill mailing.contact#last_{opened,clicked,replied}_datetime from the traces of
    every contact
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            mailing_contact
        SET
            last_opened_datetime=trace.last_opened_datetime,
            last_clicked_datetime=trace.last_clicked_datetime,
            last_replied_datetime=trace.last_replied_datetime
        FROM (
            SELECT
                res_id,
                MAX(GREATEST(open_datetime, links_click_datetime, reply_datetime))
                    AS last_opened_datetime,
                MAX(links_click_datetime) AS last_clicked_datetime,
                MAX(reply_datetime) AS last_replied_datetime
            FROM
                mailing_trace
            WHERE
                model='mailing.contact'
            AND
                res_id IS NOT NULL
            AND
                COALESCE(open_datetime, links_click_datetime, reply_datetime)
                    IS NOT NULL
            GROUP BY
                res_id
        ) trace
        WHERE
            trace.res_id=mailing_contact.id
        """,
    )


def mailing_mailing_is_template(env):
    """
    Create a template mailing for every mailing marked as favorite, v19 offered those
    as templates in the theme selector while v20 only offers mailings with is_template
    """
    env.cr.execute(
        """
        SELECT id, favorite_date
        FROM mailing_mailing
        WHERE favorite AND mailing_type='mail'
        ORDER BY favorite_date, id
        """
    )
    Mailing = env["mailing.mailing"].with_context(
        active_test=False, tracking_disable=True
    )
    for mailing_id, favorite_date in env.cr.fetchall():
        mailing = Mailing.browse(mailing_id)
        if tools.is_html_empty(mailing.body_arch):
            continue
        template = mailing.action_save_as_template()
        if favorite_date:
            template.flush_recordset()
            env.cr.execute(
                "UPDATE mailing_mailing SET create_date=%s WHERE id=%s",
                (favorite_date, template.id),
            )
            template.invalidate_recordset(["create_date"])


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "mass_mailing", "20.0.2.7/noupdate_changes.xml")
    openupgrade.m2o_to_x2m(
        env.cr,
        env["mailing.mailing"],
        "mailing_mailing",
        "mailing_filter_ids",
        "mailing_filter_id",
    )
    mailing_contact_last_datetimes(env)
    mailing_mailing_is_template(env)

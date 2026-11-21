# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from markupsafe import Markup
from openupgradelib import openupgrade


def maintenance_request_instruction_google_slide(env):
    """
    Append the link of maintenance.request#instruction_google_slide to
    maintenance.request#instruction_text, the only kind of instruction left
    """
    env.cr.execute(
        """
        SELECT
            id, instruction_google_slide
        FROM
            maintenance_request
        WHERE
            instruction_type='google_slide'
        AND
            COALESCE(instruction_google_slide, '')<>''
        """
    )
    for request_id, url in env.cr.fetchall():
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE
                maintenance_request
            SET
                instruction_text=COALESCE(instruction_text, '') || %s
            WHERE
                id=%s
            """,
            (Markup('<p><a href="%s">%s</a></p>') % (url, url), request_id),
        )


def maintenance_request_instruction_pdf(env):
    """
    Turn the file of maintenance.request#instruction_pdf into a regular attachment of
    the request
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE
            ir_attachment
        SET
            res_field=NULL,
            name=CASE
                WHEN right(lower(name), 4)='.pdf' THEN name
                ELSE name || '.pdf'
            END
        WHERE
            res_model='maintenance.request'
        AND
            res_field='instruction_pdf'
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "maintenance", "20.0.1.0/noupdate_changes.xml")
    maintenance_request_instruction_google_slide(env)
    maintenance_request_instruction_pdf(env)

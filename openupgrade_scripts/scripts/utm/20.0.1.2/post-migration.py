# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def utm_source_mailing_name(env):
    """
    Load the new name of utm.utm_source_mailing unless another source already
    uses it, as source names are unique
    """
    env.cr.execute(
        """
        SELECT id
        FROM utm_source
        WHERE
            name='Mass Mailing'
        AND
            id NOT IN (
                SELECT res_id FROM ir_model_data
                WHERE module='utm' AND name='utm_source_mailing'
            )
        """
    )
    if env.cr.fetchone():
        return
    openupgrade.load_data(env, "utm", "20.0.1.2/noupdate_changes.xml")


@openupgrade.migrate()
def migrate(env, version):
    utm_source_mailing_name(env)

# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def hr_job_website_rating(env):
    """
    Create the column beforehand so existing jobs keep an empty rating block,
    their ratings are already part of website_description
    """
    openupgrade.logged_query(
        env.cr,
        "ALTER TABLE hr_job ADD COLUMN IF NOT EXISTS website_rating jsonb",
    )


@openupgrade.migrate()
def migrate(env, version):
    hr_job_website_rating(env)

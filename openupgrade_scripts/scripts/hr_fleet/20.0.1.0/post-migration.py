# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)


def mail_activity_plan_template_offboarding_fleet(env):
    """
    The template to take back the vehicle is removed from the offboarding plan:
    delete it unless it was modified, then report it
    """
    template = env.ref("hr_fleet.offboarding_fleet", raise_if_not_found=False)
    if not template:
        return
    if template.summary == "Take Back Fleet":
        openupgrade.delete_records_safely_by_xml_id(env, ["hr_fleet.offboarding_fleet"])
    else:
        _logger.warning(
            "The activity plan template hr_fleet.offboarding_fleet (id %s, %r of the "
            "plan %r) is removed in Odoo 20 but it was modified, it is kept: review "
            "it or delete it",
            template.id,
            template.summary,
            template.plan_id.name,
        )


@openupgrade.migrate()
def migrate(env, version):
    mail_activity_plan_template_offboarding_fleet(env)

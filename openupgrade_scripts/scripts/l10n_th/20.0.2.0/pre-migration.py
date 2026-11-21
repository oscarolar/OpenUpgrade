# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_tag_xmlids = {
    "tag_th_pnd3": "PND3",
    "tag_th_income_pnd3": "Income PND3",
    "tag_th_pnd53": "PND53",
    "tag_th_income_pnd53": "Income PND53",
}


def _account_account_tag_xmlids(env):
    """
    The withholding tax tags were created on the fly from the tax report and
    are now module data: give the existing ones their xmlid, otherwise the
    module creates them again and hits the unique constraint on the name.
    """
    for xmlid, name in _tag_xmlids.items():
        env.cr.execute(
            """
            SELECT aat.id
            FROM account_account_tag aat
            JOIN ir_model_data imd
                ON imd.module = 'base' AND imd.name = 'th'
                AND imd.res_id = aat.country_id
            WHERE aat.applicability = 'taxes' AND aat.name->>'en_US' = %s
            ORDER BY aat.id
            LIMIT 1
            """,
            (name,),
        )
        row = env.cr.fetchone()
        if row:
            openupgrade.add_xmlid(
                env.cr, "l10n_th", xmlid, "account.account.tag", row[0]
            )


@openupgrade.migrate()
def migrate(env, version):
    _account_account_tag_xmlids(env)

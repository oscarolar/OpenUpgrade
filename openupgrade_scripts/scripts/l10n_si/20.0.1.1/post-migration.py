# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_recapitulative_tags = (
    "account_account_tag_l10n_si_rp_A3",
    "account_account_tag_l10n_si_rp_A4",
    "account_account_tag_l10n_si_rp_A5",
    "account_account_tag_l10n_si_rp_A6",
    "account_account_tag_l10n_si_rp_A7",
)


def _account_account_tag_keep_used(env):
    """
    The recapitulative statement tags rp_a3 to rp_a7 leave the module data and
    the new template, with no replacement. The end of the upgrade would delete
    them, and the deletion cascades to the taxes and the journal items: keep
    the ones in use as noupdate data
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_model_data imd
        SET noupdate = TRUE
        WHERE imd.module = 'l10n_si'
            AND imd.model = 'account.account.tag'
            AND imd.name = ANY(%s)
            AND imd.noupdate IS NOT TRUE
            AND (
                EXISTS (
                    SELECT 1
                    FROM account_account_tag_account_tax_repartition_line_rel rel
                    WHERE rel.account_account_tag_id = imd.res_id
                )
                OR EXISTS (
                    SELECT 1
                    FROM account_account_tag_account_move_line_rel rel
                    WHERE rel.account_account_tag_id = imd.res_id
                )
            )
        """,
        (list(_recapitulative_tags),),
    )
    return env.cr.rowcount


@openupgrade.migrate()
def migrate(env, version):
    _account_account_tag_keep_used(env)

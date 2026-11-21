# Copyright 2026 Vauxoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_added_columns = [
    ("card.card", "lang", "selection"),
    ("mailing.mailing", "card_lang", "selection"),
]

_campaign_lang = """
    COALESCE(
        (
            SELECT res_partner.lang
            FROM res_users
            JOIN res_partner ON res_partner.id=res_users.partner_id
            JOIN res_lang ON res_lang.code=res_partner.lang AND res_lang.active
            WHERE res_users.id=COALESCE(card_campaign.user_id, card_campaign.create_uid)
        ),
        (
            SELECT code FROM res_lang WHERE active
            ORDER BY code='en_US' DESC, id LIMIT 1
        )
    )
"""


def card_lang(env):
    """
    Fill card.card#lang and mailing.mailing#card_lang with the language of the
    responsible of the campaign, falling back to en_US or the first active language
    """
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE
            card_card
        SET
            lang={_campaign_lang}
        FROM
            card_campaign
        WHERE
            card_campaign.id=card_card.campaign_id
        """,
    )
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE
            mailing_mailing
        SET
            card_lang={_campaign_lang}
        FROM
            card_campaign
        WHERE
            card_campaign.id=mailing_mailing.card_campaign_id
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.add_columns(env, _added_columns)
    card_lang(env)

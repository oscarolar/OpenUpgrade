# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _account_move_l10n_es_invoice_type(env):
    """
    account.move#l10n_es_edi_verifactu_refund_reason is replaced by
    l10n_es_invoice_type of l10n_es, whose R1-R5 keys are the same refund reasons
    """
    if not openupgrade.column_exists(
        env.cr, "account_move", "l10n_es_edi_verifactu_refund_reason"
    ):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_move
        SET l10n_es_invoice_type = l10n_es_edi_verifactu_refund_reason
        WHERE l10n_es_edi_verifactu_refund_reason IN ('R1', 'R2', 'R3', 'R4', 'R5')
            AND move_type IN ('out_refund', 'in_refund')
            AND l10n_es_invoice_type
                IS DISTINCT FROM l10n_es_edi_verifactu_refund_reason
        """,
    )


def _account_move_l10n_es_regime_code(env):
    """
    account.move#l10n_es_edi_verifactu_clave_regimen is replaced by
    l10n_es_regime_code of l10n_es, which renamed some of the keys
    """
    if not openupgrade.column_exists(
        env.cr, "account_move", "l10n_es_edi_verifactu_clave_regimen"
    ):
        return
    mapping = [
        ("01", "01"),
        ("02", "02_sale"),
        ("08", "08"),
        ("11", "11_vf"),
        ("17_iva", "17"),
        ("18_iva", "18_iva"),
        ("19_iva", "19_iva"),
        ("20_iva", "20"),
        ("17_igic", "17_igic_sale"),
    ]
    for old, new in mapping:
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE account_move
            SET l10n_es_regime_code = %(new)s
            WHERE l10n_es_edi_verifactu_clave_regimen = %(old)s
                AND l10n_es_regime_code IS DISTINCT FROM %(new)s
            """,
            {"old": old, "new": new},
        )


def _res_company_l10n_es_special_vat_regime(env):
    """
    res.company#l10n_es_edi_verifactu_special_vat_regime is replaced by
    l10n_es_special_vat_regime of l10n_es
    """
    if not openupgrade.column_exists(
        env.cr, "res_company", "l10n_es_edi_verifactu_special_vat_regime"
    ):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_company
        SET l10n_es_special_vat_regime = CASE
            l10n_es_edi_verifactu_special_vat_regime
            WHEN 'recargo' THEN 'equivalence_surcharge'
            ELSE l10n_es_edi_verifactu_special_vat_regime
        END
        WHERE l10n_es_edi_verifactu_special_vat_regime IN (
                'reagyp', 'recargo', 'simplified'
            )
            AND l10n_es_special_vat_regime IS NULL
        """,
    )


def _l10n_es_edi_verifactu_issuer(env):
    """
    The chain sequence and the next batch time of the company move to the new
    l10n_es_edi_verifactu.issuer of the company and its own partner, so that
    the documents keep chaining where 19.0 stopped
    """
    if not openupgrade.column_exists(
        env.cr, "res_company", "l10n_es_edi_verifactu_chain_sequence_id"
    ):
        return
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO l10n_es_edi_verifactu_issuer (
            company_id, obligado_partner_id, chain_sequence_id, next_batch_time,
            create_uid, create_date, write_uid, write_date
        )
        SELECT
            rc.id, rc.partner_id, rc.l10n_es_edi_verifactu_chain_sequence_id,
            rc.l10n_es_edi_verifactu_next_batch_time,
            1, NOW() AT TIME ZONE 'UTC', 1, NOW() AT TIME ZONE 'UTC'
        FROM res_company rc
        WHERE (
                rc.l10n_es_edi_verifactu_chain_sequence_id IS NOT NULL
                OR rc.l10n_es_edi_verifactu_next_batch_time IS NOT NULL
            )
            AND NOT EXISTS (
                SELECT 1 FROM l10n_es_edi_verifactu_issuer issuer
                WHERE issuer.company_id = rc.id
                    AND issuer.obligado_partner_id = rc.partner_id
            )
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _account_move_l10n_es_invoice_type(env)
    _account_move_l10n_es_regime_code(env)
    _res_company_l10n_es_special_vat_regime(env)
    _l10n_es_edi_verifactu_issuer(env)

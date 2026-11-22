# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import re
from collections import defaultdict

from openupgradelib import openupgrade

from odoo import Command
from odoo.tools import float_compare

from odoo.addons.account.models.chart_template import TAX_TAG_DELIMITER

_logger = logging.getLogger(__name__)

REFUND_MOVE_TYPES = ("out_refund", "in_refund")


def remove_obsolete_tax_tag_expressions(env, module, reports=(), expressions=()):
    """
    Delete by SQL the tax_tags expressions of the account reports that the new
    version drops, before the end of the upgrade removes them with the ORM.
    The ORM removal strips the matching tags from every tax and deletes them
    (or archives them when journal items use them), and it only looks for the
    unsigned formula. Returns the ids of the tags that no remaining expression
    of their country uses and that are not module data
    """
    env.cr.execute(
        """
        SELECT expr.id
        FROM account_report_expression expr
        JOIN ir_model_data imd
            ON imd.model = 'account.report.expression'
            AND imd.res_id = expr.id
            AND imd.module = %(module)s
        JOIN account_report_line line ON line.id = expr.report_line_id
        LEFT JOIN ir_model_data rimd
            ON rimd.model = 'account.report'
            AND rimd.res_id = line.report_id
            AND rimd.module = %(module)s
        WHERE expr.engine = 'tax_tags'
            AND (rimd.name = ANY(%(reports)s) OR imd.name = ANY(%(expressions)s))
        """,
        {
            "module": module,
            "reports": list(reports),
            "expressions": list(expressions),
        },
    )
    expression_ids = [row[0] for row in env.cr.fetchall()]
    if not expression_ids:
        return []
    env.cr.execute(
        """
        SELECT DISTINCT tag.id
        FROM account_report_expression expr
        JOIN account_report_line line ON line.id = expr.report_line_id
        JOIN account_report report ON report.id = line.report_id
        JOIN account_account_tag tag
            ON tag.country_id = report.country_id
            AND tag.applicability = 'taxes'
            AND tag.name->>'en_US' = LTRIM(
                REGEXP_REPLACE(TRIM(expr.formula), '\\s+', ' ', 'g'), '-'
            )
        WHERE expr.id = ANY(%s)
        """,
        (expression_ids,),
    )
    candidate_tag_ids = [row[0] for row in env.cr.fetchall()]
    openupgrade.logged_query(
        env.cr,
        """
        DELETE FROM ir_model_data
        WHERE model = 'account.report.expression' AND res_id = ANY(%s)
        """,
        (expression_ids,),
    )
    openupgrade.logged_query(
        env.cr,
        "DELETE FROM account_report_expression WHERE id = ANY(%s)",
        (expression_ids,),
    )
    if not candidate_tag_ids:
        return []
    env.cr.execute(
        """
        SELECT tag.id
        FROM account_account_tag tag
        WHERE tag.id = ANY(%s)
            AND NOT EXISTS (
                SELECT 1
                FROM account_report_expression expr
                JOIN account_report_line line ON line.id = expr.report_line_id
                JOIN account_report report ON report.id = line.report_id
                WHERE expr.engine = 'tax_tags'
                    AND report.country_id = tag.country_id
                    AND LTRIM(
                        REGEXP_REPLACE(TRIM(expr.formula), '\\s+', ' ', 'g'), '-'
                    ) = tag.name->>'en_US'
            )
            AND NOT EXISTS (
                SELECT 1
                FROM ir_model_data imd
                WHERE imd.model = 'account.account.tag' AND imd.res_id = tag.id
            )
        """,
        (candidate_tag_ids,),
    )
    return [row[0] for row in env.cr.fetchall()]


def _template_taxes(env, template_code):
    ChartTemplate = env["account.chart.template"]
    template = ChartTemplate._get_chart_template_mapping(get_all=True).get(
        template_code
    )
    if not template:
        return {}
    env.cr.execute(
        """
        SELECT name->>'en_US', id
        FROM account_account_tag
        WHERE applicability = 'taxes' AND country_id = %s
        ORDER BY active, id DESC
        """,
        (template["country_id"],),
    )
    tag_by_name = dict(env.cr.fetchall())
    result = {}
    for xmlid, values in ChartTemplate._parse_csv(template_code, "account.tax").items():
        lines = []
        missing = []
        for fname in (
            "repartition_line_ids",
            "invoice_repartition_line_ids",
            "refund_repartition_line_ids",
        ):
            for command in values.get(fname, []):
                if command[0] != Command.CREATE:
                    continue
                line_values = command[2]
                document_type = line_values.get("document_type") or (
                    "refund" if fname.startswith("refund") else "invoice"
                )
                tag_ids = set()
                for name in (line_values.get("tag_ids") or "").split(TAX_TAG_DELIMITER):
                    name = re.sub(r"\s+", " ", name.strip())
                    if not name:
                        continue
                    tag = re.match(r"^\w+\.\w+$", name) and env.ref(
                        name, raise_if_not_found=False
                    )
                    tag_id = tag.id if tag else tag_by_name.get(name)
                    if tag_id:
                        tag_ids.add(tag_id)
                    else:
                        missing.append(name)
                lines.append(
                    (
                        document_type,
                        line_values.get("repartition_type", "tax"),
                        tag_ids,
                    )
                )
        result[xmlid] = {
            "amount_type": values.get("amount_type", "percent"),
            "amount": values.get("amount", 0.0),
            "lines": lines,
            "missing": missing,
        }
    return result


def _match_template(template, lines, amount_type, amount):
    if (
        not template
        or not any(tags for *_dummy, tags in template["lines"])
        or template["missing"]
        or template["amount_type"] != amount_type
        or float_compare(template["amount"], amount, precision_digits=4)
    ):
        return None
    template_groups = defaultdict(list)
    for document_type, repartition_type, tags in template["lines"]:
        template_groups[(document_type, repartition_type)].append(tags)
    line_groups = defaultdict(list)
    for line in lines:
        line_groups[(line[1], line[2])].append(line)
    if {key: len(value) for key, value in template_groups.items()} != {
        key: len(value) for key, value in line_groups.items()
    }:
        return None
    return [
        pair
        for key, group in line_groups.items()
        for pair in zip(group, template_groups[key], strict=True)
    ]


def _write_repartition_tags(env, to_remove, to_add):
    if to_remove:
        openupgrade.logged_query(
            env.cr,
            """
            DELETE FROM account_account_tag_account_tax_repartition_line_rel rel
            USING UNNEST(%s::int[], %s::int[]) AS old(line_id, tag_id)
            WHERE rel.account_tax_repartition_line_id = old.line_id
                AND rel.account_account_tag_id = old.tag_id
            """,
            ([line for line, _tag in to_remove], [tag for _line, tag in to_remove]),
        )
    if to_add:
        openupgrade.logged_query(
            env.cr,
            """
            INSERT INTO account_account_tag_account_tax_repartition_line_rel
                (account_tax_repartition_line_id, account_account_tag_id)
            SELECT line_id, tag_id
            FROM UNNEST(%s::int[], %s::int[]) AS new(line_id, tag_id)
            ON CONFLICT DO NOTHING
            """,
            ([line for line, _tag in to_add], [tag for _line, tag in to_add]),
        )


def retag_taxes_from_template(env, template_code, obsolete_tag_ids):
    """
    Give the taxes created from the chart template the tags that the new
    template sets on each repartition line, when one of their lines carries an
    obsolete tag and the tax still matches the template (same amount and same
    repartition lines). The journal items of those repartition lines get the
    same replacement. Taxes without a match keep their tags, and so do their
    journal items. Returns the ids of the taxes that were retagged
    """
    obsolete = set(obsolete_tag_ids)
    if not obsolete:
        return []
    env.cr.execute(
        """
        SELECT imd.name, tax.id, tax.company_id, tax.amount_type, tax.amount
        FROM ir_model_data imd
        JOIN account_tax tax ON tax.id = imd.res_id
        JOIN res_company company ON company.id = tax.company_id
        WHERE imd.module = 'account'
            AND imd.model = 'account.tax'
            AND company.chart_template = %s
            AND imd.name LIKE company.id::varchar || '\\_%%'
        """,
        (template_code,),
    )
    taxes = {
        tax_id: (name.split("_", 1)[1], amount_type, amount)
        for name, tax_id, _company_id, amount_type, amount in env.cr.fetchall()
    }
    if not taxes:
        return []
    env.cr.execute(
        """
        SELECT line.id, line.tax_id, line.document_type, line.repartition_type,
            ARRAY_REMOVE(ARRAY_AGG(rel.account_account_tag_id), NULL)
        FROM account_tax_repartition_line line
        LEFT JOIN account_account_tag_account_tax_repartition_line_rel rel
            ON rel.account_tax_repartition_line_id = line.id
        WHERE line.tax_id = ANY(%s)
        GROUP BY line.id
        ORDER BY line.tax_id, line.document_type, line.repartition_type,
            line.sequence, line.id
        """,
        (list(taxes),),
    )
    lines_by_tax = defaultdict(list)
    for line_id, tax_id, document_type, repartition_type, tag_ids in env.cr.fetchall():
        lines_by_tax[tax_id].append(
            (line_id, document_type, repartition_type, set(tag_ids))
        )
    templates = _template_taxes(env, template_code)
    to_remove = []
    to_add = []
    tag_map = []
    retagged = []
    kept = []
    for tax_id, (xmlid, amount_type, amount) in taxes.items():
        lines = lines_by_tax[tax_id]
        if not any(tags & obsolete for *_dummy, tags in lines):
            continue
        pairs = _match_template(templates.get(xmlid), lines, amount_type, amount)
        if pairs is None:
            kept.append(tax_id)
            continue
        for (line_id, document_type, repartition_type, tags), template_tags in pairs:
            new_tags = (tags - obsolete) | template_tags
            removed = tags - new_tags
            added = new_tags - tags
            to_remove += [(line_id, tag_id) for tag_id in removed]
            to_add += [(line_id, tag_id) for tag_id in added]
            tag_map += [
                (line_id, tax_id, document_type, repartition_type, old, new)
                for old in removed
                for new in (added or [None])
            ]
        retagged.append(tax_id)
    _write_repartition_tags(env, to_remove, to_add)
    if tag_map:
        _retag_move_lines(env, tag_map)
    if retagged:
        _logger.warning(
            "%s: %s taxes took the tax tags of the new chart template: %s",
            template_code,
            len(retagged),
            sorted(taxes[tax_id][0] for tax_id in retagged),
        )
    if kept:
        _logger.warning(
            "%s: %s taxes keep tax tags that no tax report of the new version "
            "uses, because the new chart template has no matching tax: %s",
            template_code,
            len(kept),
            sorted(taxes[tax_id][0] for tax_id in kept),
        )
    env.invalidate_all()
    return retagged


def _retag_move_lines(env, tag_map):
    env.cr.execute(
        """
        CREATE TEMP TABLE ou_l10n_tax_tag_map (
            line_id int, tax_id int, document_type varchar,
            repartition_type varchar, old_tag int, new_tag int
        ) ON COMMIT DROP
        """
    )
    env.cr.execute(
        """
        INSERT INTO ou_l10n_tax_tag_map
        SELECT * FROM UNNEST(
            %s::int[], %s::int[], %s::varchar[], %s::varchar[], %s::int[], %s::int[]
        )
        """,
        tuple(list(column) for column in zip(*tag_map, strict=True)),
    )
    openupgrade.logged_query(
        env.cr,
        """
        CREATE TEMP TABLE ou_l10n_tax_tag_aml ON COMMIT DROP AS
        SELECT DISTINCT rel.account_move_line_id AS aml_id, map.old_tag,
            map.new_tag
        FROM account_account_tag_account_move_line_rel rel
        JOIN account_move_line aml ON aml.id = rel.account_move_line_id
        JOIN ou_l10n_tax_tag_map map
            ON map.line_id = aml.tax_repartition_line_id
            AND map.old_tag = rel.account_account_tag_id
        UNION
        SELECT DISTINCT rel.account_move_line_id, map.old_tag, map.new_tag
        FROM account_account_tag_account_move_line_rel rel
        JOIN account_move_line aml ON aml.id = rel.account_move_line_id
        JOIN account_move move ON move.id = aml.move_id
        JOIN account_move_line_account_tax_rel tax_rel
            ON tax_rel.account_move_line_id = aml.id
        JOIN ou_l10n_tax_tag_map map
            ON map.tax_id = tax_rel.account_tax_id
            AND map.repartition_type = 'base'
            AND map.document_type = CASE
                WHEN move.move_type IN %s THEN 'refund' ELSE 'invoice' END
            AND map.old_tag = rel.account_account_tag_id
        WHERE aml.tax_repartition_line_id IS NULL
        """,
        (REFUND_MOVE_TYPES,),
    )
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO account_account_tag_account_move_line_rel
            (account_move_line_id, account_account_tag_id)
        SELECT DISTINCT aml_id, new_tag
        FROM ou_l10n_tax_tag_aml
        WHERE new_tag IS NOT NULL
        ON CONFLICT DO NOTHING
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        DELETE FROM account_account_tag_account_move_line_rel rel
        USING ou_l10n_tax_tag_aml retag
        WHERE rel.account_move_line_id = retag.aml_id
            AND rel.account_account_tag_id = retag.old_tag
        """,
    )
    env.cr.execute("DROP TABLE ou_l10n_tax_tag_aml, ou_l10n_tax_tag_map")


def archive_unused_tags(env, tag_ids):
    """Archive the obsolete tags that no tax nor journal item uses any more"""
    if not tag_ids:
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_account_tag tag
        SET active = FALSE
        WHERE tag.id = ANY(%s)
            AND tag.active
            AND NOT EXISTS (
                SELECT 1
                FROM account_account_tag_account_tax_repartition_line_rel rel
                WHERE rel.account_account_tag_id = tag.id
            )
            AND NOT EXISTS (
                SELECT 1
                FROM account_account_tag_account_move_line_rel rel
                WHERE rel.account_account_tag_id = tag.id
            )
        """,
        (list(tag_ids),),
    )


def orphan_tax_tags(env, template_code):
    """
    Tax tags of the country of the template that no tax_tags expression of
    that country uses, that are not module data and that the template does not
    reference: the tags of removed expressions, and the ones left behind when
    an expression changed its formula to a tag that already existed or changed
    its engine
    """
    template = (
        env["account.chart.template"]
        ._get_chart_template_mapping(get_all=True)
        .get(template_code)
    )
    if not template:
        return []
    referenced = {
        tag_id
        for values in _template_taxes(env, template_code).values()
        for *_dummy, tags in values["lines"]
        for tag_id in tags
    }
    env.cr.execute(
        """
        SELECT tag.id
        FROM account_account_tag tag
        WHERE tag.country_id = %s
            AND tag.applicability = 'taxes'
            AND NOT EXISTS (
                SELECT 1
                FROM account_report_expression expr
                JOIN account_report_line line ON line.id = expr.report_line_id
                JOIN account_report report ON report.id = line.report_id
                WHERE expr.engine = 'tax_tags'
                    AND report.country_id = tag.country_id
                    AND LTRIM(
                        REGEXP_REPLACE(TRIM(expr.formula), '\\s+', ' ', 'g'), '-'
                    ) = tag.name->>'en_US'
            )
            AND NOT EXISTS (
                SELECT 1
                FROM ir_model_data imd
                WHERE imd.model = 'account.account.tag' AND imd.res_id = tag.id
            )
        """,
        (template["country_id"],),
    )
    return [row[0] for row in env.cr.fetchall() if row[0] not in referenced]


def migrate_obsolete_tax_tags(env, module, template_codes, reports=(), expressions=()):
    """
    Remove the obsolete expressions without touching the taxes, give the
    template taxes the new tags in place of the orphan ones and archive the
    orphan tags nothing uses. Returns the ids of the retagged taxes
    """
    remove_obsolete_tax_tag_expressions(
        env, module, reports=reports, expressions=expressions
    )
    retagged = []
    for template_code in template_codes:
        orphans = orphan_tax_tags(env, template_code)
        retagged += retag_taxes_from_template(env, template_code, orphans)
        archive_unused_tags(env, orphans)
    return retagged

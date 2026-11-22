# Copyright 2026 Vauxoo (https://www.vauxoo.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import importlib.util
import json
import os

from odoo.tests import TransactionCase

from . import l10n_tax_tags


def load_script(module, version, script):
    path = os.path.join(os.path.dirname(__file__), "scripts", module, version, script)
    spec = importlib.util.spec_from_file_location(f"ou20_{module}_{version}", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class L10nTaxTagsCase(TransactionCase):
    country = None
    template_code = None

    def setUp(self):
        super().setUp()
        self.env.cr.execute(
            "SELECT value FROM ir_config_parameter WHERE key = %s",
            (f"ou20.l10n_tax_tags.{self.country}",),
        )
        row = self.env.cr.fetchone()
        if not row:
            self.skipTest(f"data for {self.country} was not loaded")
        self.snapshot = json.loads(row[0])
        self.company = self.env["res.company"].search(
            [("name", "=", f"OU20 TAGS {self.country.upper()}")]
        )
        self.Tag = self.env["account.account.tag"].with_context(
            active_test=False, lang="en_US"
        )

    def _names(self, tags):
        return sorted(tags.with_context(lang="en_US").mapped("name"))

    def _tax(self, xmlid):
        return self.env.ref(xmlid)

    def _sorted_lines(self, tax):
        return tax.repartition_line_ids.sorted(
            lambda line: (
                line.document_type,
                line.repartition_type,
                line.sequence,
                line.id,
            )
        )

    def _tax_state(self, tax):
        return [
            [line.document_type, line.repartition_type, self._names(line.tag_ids)]
            for line in self._sorted_lines(tax)
        ]

    def _template_state(self, xmlid):
        template = l10n_tax_tags._template_taxes(self.env, self.template_code).get(
            xmlid.split(".", 1)[1].split("_", 1)[1]
        )
        if not template:
            return None
        return [
            [document_type, repartition_type, self._names(self.Tag.browse(tags))]
            for document_type, repartition_type, tags in sorted(
                template["lines"], key=lambda line: (line[0], line[1])
            )
        ]

    def tax_outcome(self):
        """Classify every tax of the snapshot as unchanged or retagged, and
        fail when a tax lost tags without taking the template ones"""
        self.env.invalidate_all()
        outcome = {"unchanged": set(), "retagged": set()}
        for xmlid, before in self.snapshot["taxes"].items():
            tax = self._tax(xmlid)
            short = xmlid.split(".", 1)[1].split("_", 1)[1]
            lines = self._sorted_lines(tax)
            self.assertEqual(
                [[line.document_type, line.repartition_type] for line in lines],
                [line[:2] for line in before],
                xmlid,
            )
            if [sorted(line.tag_ids.ids) for line in lines] == [
                line[3] for line in before
            ]:
                outcome["unchanged"].add(short)
                continue
            self.assertEqual(self._tax_state(tax), self._template_state(xmlid), xmlid)
            outcome["retagged"].add(short)
        tag_ids = {
            tag_id
            for lines in self.snapshot["taxes"].values()
            for line in lines
            for tag_id in line[3]
        }
        self.assertEqual(sorted(self.Tag.browse(tag_ids).exists().ids), sorted(tag_ids))
        return outcome

    def check_move_lines(self):
        """The journal items keep the tags of their repartition line"""
        self.env.invalidate_all()
        lines = self.env["account.move.line"].browse(
            [int(line_id) for line_id in self.snapshot["move_lines"]]
        )
        self.assertTrue(lines)
        for line in lines:
            if line.tax_repartition_line_id:
                expected = line.tax_repartition_line_id.tag_ids
            else:
                document_type = (
                    "refund"
                    if line.move_id.move_type in l10n_tax_tags.REFUND_MOVE_TYPES
                    else "invoice"
                )
                expected = line.tax_ids.repartition_line_ids.filtered(
                    lambda rep, document_type=document_type: (
                        rep.repartition_type == "base"
                        and rep.document_type == document_type
                    )
                ).tag_ids
            self.assertEqual(
                self._names(line.tax_tag_ids), self._names(expected), line.name
            )

    def check_rerun(self, script, *args):
        before = {
            xmlid: self._tax_state(self._tax(xmlid)) for xmlid in self.snapshot["taxes"]
        }
        self.assertFalse(script._tax_tags(self.env, *args))
        self.env.invalidate_all()
        self.assertEqual(
            {
                xmlid: self._tax_state(self._tax(xmlid))
                for xmlid in self.snapshot["taxes"]
            },
            before,
        )

    def check_obsolete_report_data(self, module, script):
        for report in getattr(script, "_obsolete_reports", ()):
            self.assertFalse(
                self.env.ref(f"{module}.{report}", raise_if_not_found=False), report
            )
        self.assertFalse(
            self.env["ir.model.data"].search(
                [
                    ("module", "=", module),
                    ("model", "=", "account.report.expression"),
                    ("name", "in", list(getattr(script, "_obsolete_expressions", ()))),
                ]
            )
        )

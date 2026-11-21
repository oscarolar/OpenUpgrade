# Copyright 2026 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import ast
import logging
import os
import re
from collections import defaultdict, namedtuple

from markupsafe import Markup, escape
from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)

_operation_field_mapping = {
    "c": "perm_create",
    "r": "perm_read",
    "u": "perm_write",
    "d": "perm_unlink",
}
_allow_widen_variable = "OPENUPGRADE_IR_ACCESS_ALLOW_WIDEN"
_renamed_fields = {
    "acc_number": "account_number",
    "acc_holder_name": "holder_name",
    "sanitized_acc_number": "sanitized_account_number",
}

Rule = namedtuple(
    "Rule",
    (
        "id",
        "name",
        "model_id",
        "groups",
        "operations",
        "domain",
        "standard",
        "customized",
        "counterpart",
    ),
)


def _normalize_domain(domain):
    """
    Return a representation of a domain string that does not depend on its formatting
    """
    domain = (domain or "").strip() or "[]"
    try:
        normalized = ast.dump(ast.parse(domain, mode="eval"))
    except SyntaxError:
        return " ".join(domain.split())
    if normalized in (
        ast.dump(ast.parse("[]", mode="eval")),
        ast.dump(ast.parse("[(1, '=', 1)]", mode="eval")),
    ):
        return "TRUE"
    return normalized


def _rename_domain_fields(domain):
    """
    Return the domain with the fields renamed in v20 replaced by their new name
    """
    for old_name, new_name in _renamed_fields.items():
        domain = re.sub(
            rf"(?<=['\".]){re.escape(old_name)}(?=['\".])", new_name, domain or ""
        )
    return domain


def _operations(row):
    return "".join(
        operation
        for operation, field_name in _operation_field_mapping.items()
        if row[field_name]
    )


class AccessMigration:
    """
    Convert the ir.model.access and ir.rule records users created or changed in v19 to
    ir.access.

    In v19, a user needs an ir.model.access for the operation, and sees the records
    matching all global rules and any of the group rules of their groups. In v20,
    ir.access records with a group are permissions combined with OR, the ones without
    group are restrictions combined with AND. So a custom group rule only restricts
    in v20 if no other permission of the user is wider, and whatever cannot be kept as
    restrictive as it was makes the migration fail unless the environment variable
    OPENUPGRADE_IR_ACCESS_ALLOW_WIDEN is set.
    """

    def __init__(self, env):
        self.env = env
        self.IrAccess = env["ir.access"].with_context(active_test=False)
        self.ResGroups = env["res.groups"]
        self.allow_widen = os.environ.get(_allow_widen_variable) == "1"
        self._closures = {}
        self._inactive_rules = None
        self.notes = []
        self.modules = self._get_installed_modules()
        self.customized = self._get_customized()
        self.rules = self._get_rules()
        self.acl_groups = defaultdict(set)
        self.manual_acls = []
        self._get_model_access()
        self.group_rules = defaultdict(list)
        for rule in self.rules:
            if rule.groups:
                for operation in rule.operations:
                    self.group_rules[(rule.model_id, operation)].append(rule)
        self.touched_models = {
            rule.model_id for rule in self.rules if self._touched(rule)
        } | {model_id for _name, model_id, _group_id, _operations in self.manual_acls}
        self.standard_permissions = self.IrAccess.search(
            [
                ("model_id", "in", list(self.touched_models)),
                ("active", "=", True),
                ("group_id", "!=", False),
            ]
        ).filtered("is_standard")
        self.permissions = defaultdict(set)
        self.permission_origins = defaultdict(set)
        self.created = self.IrAccess.browse()
        self.created_inactive = self.IrAccess.browse()
        self.replaced = self.IrAccess.browse()
        self.deactivated = self.IrAccess.browse()
        self.activated = self.IrAccess.browse()
        self.unpreservable = []

    def _get_installed_modules(self):
        """
        Return the installed modules that exist in v20. Records with an xmlid of any
        other module or namespace are not recreated from module data, so they are
        custom records
        """
        self.env.cr.execute(
            """
            SELECT name FROM ir_module_module
            WHERE state IN ('installed', 'to upgrade', 'to install')
            """
        )
        IrModuleModule = self.env["ir.module.module"]
        return [
            name
            for (name,) in self.env.cr.fetchall()
            if IrModuleModule.get_module_info(name)
        ]

    def _get_customized(self):
        table = openupgrade.get_legacy_name("ir_rule_customized")
        if not openupgrade.table_exists(self.env.cr, table):
            return {}
        self.env.cr.execute(f"SELECT * FROM {table}")
        return {row["rule_id"]: row for row in self.env.cr.dictfetchall()}

    def _get_counterpart(self, xmlid):
        """
        Return the ir.access record that has the xmlid a v19 ir.rule had
        """
        if not xmlid:
            return self.IrAccess.browse()
        record = self.env.ref(
            xmlid.removesuffix("_ir_rule"), raise_if_not_found=False
        )
        if record and record._name == "ir.access":
            return record
        return self.IrAccess.browse()

    def _query_rules(self, active):
        self.env.cr.execute(
            """
            SELECT
                ir_rule.id, COALESCE(ir_rule.name, 'ir.rule,' || ir_rule.id) AS name,
                ir_rule.model_id, ir_rule.domain_force, ir_rule.perm_create,
                ir_rule.perm_read, ir_rule.perm_write, ir_rule.perm_unlink,
                ARRAY(
                    SELECT group_id FROM rule_group_rel
                    WHERE rule_group_id=ir_rule.id
                ) AS group_ids,
                (
                    SELECT module || '.' || name FROM ir_model_data
                    WHERE model='ir.rule' AND res_id=ir_rule.id AND module=ANY(%s)
                    ORDER BY id LIMIT 1
                ) AS xmlid
            FROM
                ir_rule
            JOIN
                ir_model ON ir_model.id=ir_rule.model_id
            WHERE
                ir_rule.active=%s
            ORDER BY
                ir_rule.id
            """,
            (self.modules, active),
        )
        result = []
        for row in self.env.cr.dictfetchall():
            operations = _operations(row)
            if not operations:
                self.notes.append(
                    f"Record rule {row['name']} ({row['id']}) applies to no "
                    "operation, it is not migrated"
                )
                continue
            result.append(
                Rule(
                    row["id"],
                    row["name"],
                    row["model_id"],
                    frozenset(row["group_ids"]),
                    operations,
                    row["domain_force"],
                    bool(row["xmlid"]),
                    self.customized.get(row["id"]) if row["xmlid"] else None,
                    self._get_counterpart(row["xmlid"]),
                )
            )
        return result

    def _get_rules(self):
        return self._query_rules(True)

    def _get_inactive_rules(self):
        if self._inactive_rules is None:
            self._inactive_rules = self._query_rules(False)
        return self._inactive_rules

    def _get_model_access(self):
        self.env.cr.execute(
            """
            SELECT
                ir_model_access.id, ir_model_access.name, model_id, group_id,
                perm_create, perm_read, perm_write, perm_unlink,
                EXISTS (
                    SELECT 1 FROM ir_model_data
                    WHERE model='ir.model.access' AND res_id=ir_model_access.id
                    AND module=ANY(%s)
                ) AS standard
            FROM
                ir_model_access
            JOIN
                ir_model ON ir_model.id=ir_model_access.model_id
            WHERE
                ir_model_access.active
            ORDER BY
                ir_model_access.id
            """,
            (self.modules,),
        )
        for row in self.env.cr.dictfetchall():
            operations = _operations(row)
            for operation in operations:
                self.acl_groups[(row["model_id"], operation)].add(row["group_id"])
            if not row["standard"]:
                if operations:
                    self.manual_acls.append(
                        (row["name"], row["model_id"], row["group_id"], operations)
                    )
                else:
                    self.notes.append(
                        f"Model access {row['name']} ({row['id']}) grants no "
                        "operation, it is not migrated"
                    )

    def _touched(self, rule):
        """
        Tell if a rule was created or changed by users. Rules that only were activated
        and have an ir.access with their xmlid are handled by activating that record
        """
        if not rule.standard:
            return True
        return bool(rule.customized) and not (
            self._only_active_differs(rule) and rule.counterpart
        )

    def _down(self, group_id):
        """
        Return the ids of the groups a user of the group has
        """
        key = ("down", group_id)
        if key not in self._closures:
            group = self.ResGroups.browse(group_id)
            self._closures[key] = set((group | group.all_implied_ids).ids)
        return self._closures[key]

    def _up(self, group_id):
        """
        Return the ids of the groups whose users have the group
        """
        key = ("up", group_id)
        if key not in self._closures:
            group = self.ResGroups.browse(group_id)
            self._closures[key] = set((group | group.all_implied_by_ids).ids)
        return self._closures[key]

    def _applicable_rules(self, group_id, model_id, operation):
        """
        Return the v19 group rules that apply to a user who only has the group
        """
        groups = self._down(group_id)
        return [
            rule
            for rule in self.group_rules[(model_id, operation)]
            if rule.groups & groups
        ]

    def _restricts(self, rules):
        """
        Tell if a set of v19 group rules restricts access because of a rule that was
        created or changed by users
        """
        return (
            bool(rules)
            and not any(_normalize_domain(rule.domain) == "TRUE" for rule in rules)
            and any(self._touched(rule) for rule in rules)
        )

    def _model_name(self, model_id):
        return self.env["ir.model"].browse(model_id).model

    def _group_name(self, group_id):
        return self.ResGroups.browse(group_id).display_name if group_id else "no group"

    def _create(self, vals, critical=False, note=None):
        """
        Create an active ir.access record. If its domain is not valid in v20, retry
        with the fields that were renamed. If it still fails, losing a critical record
        makes the migration fail, others are created inactive
        """
        if note:
            vals = dict(vals, note=Markup("<p>%s</p>") % note)
        error = None
        for domain in dict.fromkeys(
            [vals.get("domain"), _rename_domain_fields(vals.get("domain")) or None]
        ):
            try:
                with self.env.cr.savepoint():
                    record = self.IrAccess.create(dict(vals, domain=domain))
                self.created += record
                return record
            except Exception as e:  # noqa: BLE001
                error = e
        description = (
            f"{vals['name']} on {self._model_name(vals['model_id'])}"
            f"[{vals['operation']}] with domain {vals.get('domain')}: {error}"
        )
        if critical:
            self.unpreservable.append(
                f"Restriction {description} is not valid in v20, so it would be lost"
            )
        else:
            self.notes.append(
                f"Permission {description} is not valid in v20, it is inactive"
            )
        record = self.IrAccess.create(
            dict(
                vals,
                active=False,
                note=Markup("<p>%s</p><p>%s</p>") % (note or "", error),
            )
        )
        self.created_inactive += record
        return record

    def _customization_note(self, rule):
        return escape(
            "Record rule %(xmlid)s was customized in v19. "
            "Domain: %(domain)s (standard: %(std_domain)s)."
        ) % {
            "xmlid": rule.customized["xmlid"],
            "domain": rule.domain or "[]",
            "std_domain": rule.customized["std_domain"] or "[]",
        }

    def _only_active_differs(self, rule):
        customized = rule.customized
        return bool(
            customized
            and customized["diff_active"]
            and not customized["diff_domain"]
            and not customized["diff_perms"]
            and not customized["diff_groups"]
        )

    def _activate_counterpart(self, rule):
        """
        Rules that are inactive in the module data and were activated in v19, by code
        or by users, have their ir.access activated too
        """
        if not rule.counterpart:
            return False
        if not rule.counterpart.active:
            rule.counterpart.active = True
            self.activated += rule.counterpart
        return True

    def global_rules(self):
        """
        Global rules are restrictions in v20 too. Adding one can only narrow access,
        so the ones users created or changed are always created as active restrictions
        """
        for rule in self.rules:
            if rule.groups or not self._touched(rule):
                continue
            vals = {
                "name": f"Migrated from v19 ({rule.name})",
                "operation": rule.operations,
                "group_id": False,
                "model_id": rule.model_id,
                "domain": rule.domain,
            }
            if not rule.standard:
                self._create(vals, critical=True)
                continue
            if self._only_active_differs(rule) and self._activate_counterpart(rule):
                continue
            customized = rule.customized
            counterpart = rule.counterpart
            if not customized["diff_domain"] and not customized["diff_groups"]:
                if not set(rule.operations) - set(counterpart.operation or ""):
                    continue
            same_role = bool(
                counterpart
                and counterpart.active
                and not counterpart.group_id
                and not customized["diff_perms"]
                and not customized["diff_groups"]
                and set(counterpart.operation) <= set(rule.operations)
                and _normalize_domain(counterpart.domain)
                == _normalize_domain(customized["std_domain"])
            )
            note = self._customization_note(rule)
            if same_role:
                record = self._create(
                    dict(vals, name=f"{counterpart.name} (customized in v19)"),
                    critical=True,
                    note=note,
                )
                if record.active:
                    counterpart.active = False
                    self.deactivated += counterpart
                    self.replaced += record
                continue
            self._create(
                dict(vals, name=f"Customized in v19 ({customized['xmlid']})"),
                critical=True,
                note=note,
            )

    def inactive_standard_rules(self):
        """
        Rules provided by modules that users deactivated in v19
        """
        for rule in self._get_inactive_rules():
            customized = rule.customized
            if not customized or not customized["std_active"]:
                continue
            counterpart = rule.counterpart
            model = self._model_name(rule.model_id)
            if counterpart and bool(counterpart.group_id) == bool(rule.groups):
                if counterpart.active:
                    counterpart.active = False
                    self.deactivated += counterpart
                continue
            if rule.groups:
                self.unpreservable.append(
                    f"Group rule {customized['xmlid']} on {model} was deactivated in "
                    "v19 and has no ir.access with the same role in v20, so the "
                    "access it granted cannot be removed"
                )
            for group_id in rule.groups or [False]:
                self.created_inactive += self.IrAccess.create(
                    {
                        "name": f"Customized in v19 ({customized['xmlid']})",
                        "operation": rule.operations,
                        "group_id": group_id,
                        "model_id": rule.model_id,
                        "domain": rule.domain,
                        "active": False,
                        "note": Markup("<p>%s</p>")
                        % escape(
                            "Record rule %s was deactivated in v19 and has no "
                            "ir.access with the same role in v20."
                        )
                        % customized["xmlid"],
                    }
                )

    def group_rules_customized(self):
        """
        A group rule provided by a module whose domain was changed is a permission with
        the standard domain in v20, which has to go in favour of the changed one
        """
        for rule in self.rules:
            if not rule.groups or not rule.customized:
                continue
            if self._only_active_differs(rule):
                self._activate_counterpart(rule)
                continue
            customized = rule.customized
            if not customized["diff_domain"]:
                continue
            counterpart = rule.counterpart
            if (
                counterpart
                and counterpart.group_id.id in rule.groups
                and _normalize_domain(counterpart.domain)
                == _normalize_domain(customized["std_domain"])
            ):
                if counterpart.active:
                    counterpart.active = False
                    self.deactivated += counterpart
                    self.standard_permissions -= counterpart
                continue
            self.unpreservable.append(
                f"Group rule {customized['xmlid']} on "
                f"{self._model_name(rule.model_id)} has a domain changed in v19 "
                f"({rule.domain}) and no ir.access with the same role in v20, so the "
                "standard domain would apply"
            )

    def _add_permission(self, group_id, model_id, domain, operation, origin):
        key = (group_id, model_id, domain)
        self.permissions[key].add(operation)
        self.permission_origins[key].add(origin)

    def group_rules_permissions(self):
        """
        A group rule users created or changed gives its domain to the groups that had
        model access for the operation and are affected by the rule
        """
        ineffective = defaultdict(set)
        rules = {rule.id: rule for rule in self.rules}
        for rule in self.rules:
            if not rule.groups or not self._touched(rule):
                continue
            if self._only_active_differs(rule) and rule.counterpart:
                continue
            for group_id in rule.groups:
                for operation in rule.operations:
                    acl_groups = self.acl_groups[(rule.model_id, operation)]
                    if None in acl_groups or acl_groups & self._down(group_id):
                        targets = {group_id}
                    else:
                        targets = acl_groups & self._up(group_id)
                    if not targets:
                        ineffective[(rule.id, group_id)].add(operation)
                    for target in targets:
                        self._add_permission(
                            target, rule.model_id, rule.domain, operation, rule.name
                        )
        for (rule_id, group_id), operations in ineffective.items():
            rule = rules[rule_id]
            self.created_inactive += self.IrAccess.create(
                {
                    "name": f"Migrated from v19 ({rule.name})",
                    "operation": "".join(o for o in "crud" if o in operations),
                    "group_id": group_id,
                    "model_id": rule.model_id,
                    "domain": rule.domain,
                    "active": False,
                    "note": Markup(
                        "<p>No group of the users this v19 record rule applied to "
                        "had model access for these operations, so it had no effect."
                        "</p>"
                    ),
                }
            )

    def manual_model_access(self):
        """
        A custom ir.model.access was restricted by the group rules that applied to its
        group, be it rules provided by modules or custom ones
        """
        everyone = self.env.ref("base.group_everyone")
        for name, model_id, group_id, operations in self.manual_acls:
            for operation in operations:
                if not group_id:
                    if self.group_rules[(model_id, operation)]:
                        self.notes.append(
                            f"Model access {name} without group on "
                            f"{self._model_name(model_id)}[{operation}] is only "
                            "kept for the groups that have record rules"
                        )
                        continue
                    self._add_permission(everyone.id, model_id, None, operation, name)
                    continue
                rules = self._applicable_rules(group_id, model_id, operation)
                if not rules or any(
                    _normalize_domain(rule.domain) == "TRUE" for rule in rules
                ):
                    self._add_permission(group_id, model_id, None, operation, name)
                    continue
                for rule in rules:
                    domain = rule.domain
                    if not self._touched(rule) and rule.counterpart:
                        domain = rule.counterpart.domain
                    self._add_permission(group_id, model_id, domain, operation, name)
                    self.permission_origins[(group_id, model_id, domain)].add(
                        rule.name
                    )

    def narrow_standard_permissions(self):
        """
        A standard permission without domain makes the group rules users created or
        changed for its group useless. Replace it by a copy for the operations that
        were not restricted
        """
        narrowed = {}
        for permission in self.standard_permissions:
            if _normalize_domain(permission.domain) != "TRUE":
                continue
            operations = {
                operation
                for operation in permission.operation
                if self._restricts(
                    self._applicable_rules(
                        permission.group_id.id, permission.model_id.id, operation
                    )
                )
            }
            if not operations:
                continue
            narrowed[permission] = operations
            permission.active = False
            self.deactivated += permission
            remaining = "".join(
                o for o in permission.operation if o not in operations
            )
            if remaining:
                self.replaced += self._create(
                    {
                        "name": f"{permission.name} (customized in v19)",
                        "operation": remaining,
                        "group_id": permission.group_id.id,
                        "model_id": permission.model_id.id,
                        "domain": False,
                    },
                    note=escape(
                        "The standard access is replaced because custom record rules "
                        "restrict the operations %s for this group."
                    )
                    % "".join(sorted(operations)),
                )
        for rule in self.rules:
            if not rule.groups or not self._touched(rule):
                continue
            for group_id in rule.groups:
                for operation in rule.operations:
                    if not self._restricts(
                        self._applicable_rules(group_id, rule.model_id, operation)
                    ):
                        continue
                    for permission in self.standard_permissions:
                        if (
                            permission.model_id.id != rule.model_id
                            or operation not in permission.operation
                            or _normalize_domain(permission.domain) != "TRUE"
                            or permission.group_id.id == group_id
                            or permission.group_id.id not in self._down(group_id)
                            or operation in narrowed.get(permission, ())
                        ):
                            continue
                        self.unpreservable.append(
                            f"Group rule {rule.name} for {self._group_name(group_id)} "
                            f"on {self._model_name(rule.model_id)}[{operation}] "
                            f"({rule.domain}) cannot restrict in v20: the standard "
                            f"access {permission.name} grants all records to "
                            f"{permission.group_id.display_name}, which the users of "
                            "the group have too"
                        )

    def create_permissions(self):
        for (group_id, model_id, domain), operations in self.permissions.items():
            origins = sorted(self.permission_origins[(group_id, model_id, domain)])
            self._create(
                {
                    "name": f"Migrated from v19 ({', '.join(origins)})",
                    "operation": "".join(o for o in "crud" if o in operations),
                    "group_id": group_id,
                    "model_id": model_id,
                    "domain": domain,
                }
            )

    def inactive_custom_records(self):
        """
        Custom ir.model.access and ir.rule records that were inactive in v19 are kept
        as inactive ir.access records
        """
        self.env.cr.execute(
            """
            SELECT
                ir_model_access.name, perm_create, perm_read, perm_write,
                perm_unlink, model_id, group_id
            FROM
                ir_model_access
            JOIN
                ir_model ON ir_model.id=ir_model_access.model_id
            WHERE
                NOT ir_model_access.active
            AND NOT EXISTS (
                SELECT 1 FROM ir_model_data
                WHERE model='ir.model.access' AND res_id=ir_model_access.id
                AND module=ANY(%s)
            )
            """,
            (self.modules,),
        )
        records = [
            (row["name"], row["model_id"], row["group_id"], _operations(row), None)
            for row in self.env.cr.dictfetchall()
        ]
        for rule in self._get_inactive_rules():
            if rule.standard:
                continue
            for group_id in rule.groups or [False]:
                records.append(
                    (rule.name, rule.model_id, group_id, rule.operations, rule.domain)
                )
        for name, model_id, group_id, operations, domain in records:
            if not operations:
                continue
            self.created_inactive += self.IrAccess.create(
                {
                    "name": f"Migrated from v19 ({name})",
                    "operation": operations,
                    "group_id": group_id,
                    "model_id": model_id,
                    "domain": domain,
                    "active": False,
                    "note": Markup("<p>This record was inactive in v19.</p>"),
                }
            )

    def run(self):
        self.global_rules()
        self.inactive_standard_rules()
        self.group_rules_customized()
        self.group_rules_permissions()
        self.manual_model_access()
        self.narrow_standard_permissions()
        self.create_permissions()
        self.inactive_custom_records()
        self.report()

    def _links(self, records):
        return Markup("").join(
            Markup('<li><a href="/odoo/%s/%s">%s</a></li>')
            % (record._name, record.id, record.display_name)
            for record in records
        )

    def report(self):
        for note in self.notes + self.unpreservable:
            openupgrade.message(self.env.cr, "base", "ir_access", None, "%s", note)
        sections = (
            (
                self.created.filtered("active") - self.replaced,
                "Access records created from your custom model access and record "
                "rules:",
            ),
            (
                self.replaced,
                "Custom copies that replace standard access records, because you "
                "changed the domain of a standard record rule or because your record "
                "rules restrict the group:",
            ),
            (
                self.deactivated,
                "Standard access records that were deactivated, because they are "
                "replaced or because you deactivated their record rule in v19:",
            ),
            (
                self.activated,
                "Standard access records that were activated like their record rule "
                "in v19:",
            ),
            (
                self.created_inactive,
                "Inactive access records for what has no equivalent in v20, was "
                "inactive in v19 or is not valid any more. Review their notes:",
            ),
        )
        for records, text in sections:
            for access in records:
                openupgrade.message(
                    self.env.cr,
                    "base",
                    "ir_access",
                    None,
                    "%s %s (%s, %s, group %s, domain %s, active=%s)",
                    text,
                    access.id,
                    access.name,
                    access.model_id.model,
                    access.group_id.display_name,
                    access.domain,
                    access.active,
                )
        if self.unpreservable and not self.allow_widen:
            raise Exception(  # pylint: disable=broad-exception-raised
                "Some v19 access restrictions cannot be kept in v20, users would "
                "get access to more records than before:\n- %s\n"
                "Fix these rules in the v19 database and migrate it again, or set "
                "the environment variable %s=1 to migrate anyway and review the "
                "access records afterwards."
                % ("\n- ".join(self.unpreservable), _allow_widen_variable)
            )
        all_access = (
            self.created + self.created_inactive + self.deactivated + self.activated
        )
        if not all_access and not self.notes:
            return
        body = Markup(
            """
            <div class="alert alert-warning">Custom record rules and model access</div>
            <p>You have customized your model access rules.
            Note the v19 approach does not map exactly to v20, so you need to
            review and test carefully that the migrated access records for the
            following models do what you expect.</p>
            <p>In v20, access records with a group are permissions, a user gets the
            records allowed by any of them. Access records without group are
            restrictions that apply to everyone. The migration keeps access at most as
            wide as it was in v19, so some users may see fewer records than before.</p>
            <p>Models with custom access:</p>
            <ul>%s</ul>
            """
        ) % self._links(all_access.model_id)
        for records, text in sections:
            if records:
                body += Markup("<p>%s</p><ul>%s</ul>") % (text, self._links(records))
        if self.unpreservable:
            body += Markup(
                "<p>These restrictions could not be kept, access is wider than in "
                "v19:</p><ul>%s</ul>"
            ) % Markup("").join(
                Markup("<li>%s</li>") % line for line in self.unpreservable
            )
        if self.notes:
            body += Markup("<p>Notes:</p><ul>%s</ul>") % Markup("").join(
                Markup("<li>%s</li>") % line for line in self.notes
            )
        target = "discuss.channel" in self.env and self.env.ref(
            "mail.channel_admin", raise_if_not_found=False
        )
        if not target and "mail.thread" in self.env:
            target = self.env.ref("base.partner_admin", raise_if_not_found=False)
        if target:
            target.message_post(body=body, message_type="comment")
        else:
            _logger.warning("No place to post the access migration report: %s", body)


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.disable_invalid_filters(env)
    AccessMigration(env).run()

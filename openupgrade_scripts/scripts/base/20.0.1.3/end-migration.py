# Copyright 2026 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import ast
from collections import namedtuple

from markupsafe import Markup, escape
from openupgradelib import openupgrade

_operation_field_mapping = {
    "c": "perm_create",
    "r": "perm_read",
    "u": "perm_write",
    "d": "perm_unlink",
}


class SetOfDomainWithOrigin(dict):
    """
    Store domains for some permission/restriction with the ir.model.access id that
    enables the operation
    """

    def __init__(self, origin):
        self.origin = origin

    def add(self, domain, origin):
        if domain in self:
            self[domain].add(origin)
        else:
            self[domain] = {origin}


AccessTuple = namedtuple("AccessTuple", ("group", "model", "operation"))


def _ir_access_get_v19_permissions(env):
    """
    Return custom permission domains per operation as seen in v19.

    Only consider custom records, not changed module records as we don't know their
    original value at this point.
    """
    IrModel = env["ir.model"]
    ResGroups = env["res.groups"]
    accesstuple2domains = {}
    accesstuples_manual = set()
    skipped_rules = {}
    applied_rules = set()
    operation_field_mapping = _operation_field_mapping

    def custom_record(column, model):
        return f"""
        {column} NOT IN (
            SELECT res_id
            FROM ir_model_data
            WHERE model='{model}'
            AND module NOT IN (
                '__export__', '__custom__', 'studio_customization'
            )
        )
        """

    env.cr.execute(
        f"""
        SELECT
            name, perm_create, perm_read, perm_write, perm_unlink, model_id, group_id,
            NOT {custom_record("id", "ir.model.access")} AS has_xmlid
        FROM
            ir_model_access
        WHERE
            active
        """
    )
    for row in env.cr.dictfetchall():
        for operation, field_name in operation_field_mapping.items():
            if not row[field_name]:
                continue
            group = ResGroups.browse(row["group_id"])
            model = IrModel.browse(row["model_id"])
            accesstuple = AccessTuple(group, model, operation)
            if not row["has_xmlid"]:
                accesstuples_manual.add(accesstuple)
            for implied_by_group in group.all_implied_by_ids or [group]:
                key = AccessTuple(implied_by_group, model, operation)
                accesstuple2domains[key] = SetOfDomainWithOrigin(row["name"])

    env.cr.execute(
        f"""
        SELECT
            COALESCE(name, 'ir.rule,'||id) name, perm_create, perm_read, perm_write,
            perm_unlink, domain_force, model_id, group_id
        FROM
            ir_rule
        LEFT JOIN
            rule_group_rel
        ON
            rule_group_rel.rule_group_id=ir_rule.id
        WHERE
            ir_rule.active
        AND (
            perm_create OR
            perm_read OR
            perm_write OR
            perm_unlink
        )
        AND
            {custom_record("ir_rule.id", "ir.rule")}
        """
    )

    for row in env.cr.dictfetchall():
        for operation, field_name in operation_field_mapping.items():
            if not row[field_name]:
                continue
            key = AccessTuple(
                ResGroups.browse(row["group_id"]),
                IrModel.browse(row["model_id"]),
                operation,
            )
            # in general, don't consider domains for operations that aren't allowed
            if key not in accesstuple2domains:
                global_key = (ResGroups,) + key[1:]
                if global_key in accesstuple2domains:
                    # but if there's a blanket permission, consider the domain
                    accesstuple2domains[key] = SetOfDomainWithOrigin(
                        accesstuple2domains[global_key].origin
                    )
                elif not key.group:
                    for accesstuple, domains in accesstuple2domains.items():
                        if (
                            accesstuple.model == key.model
                            and accesstuple.operation == key.operation
                        ):
                            # also consider domains of restrictions if there are
                            # permissions for it
                            accesstuple2domains[key] = SetOfDomainWithOrigin(
                                domains.origin
                            )
                            break
                    else:
                        skipped_rules.setdefault(
                            (key.group, key.model, row["domain_force"], row["name"]),
                            [],
                        ).append(operation)
                        continue
                else:
                    skipped_rules.setdefault(
                        (key.group, key.model, row["domain_force"], row["name"]), []
                    ).append(operation)
                    continue
            accesstuple2domains[key].add(row["domain_force"], row["name"])
            applied_rules.add((key.group, key.model, row["domain_force"], row["name"]))

    for rule in applied_rules:
        skipped_rules.pop(rule, None)
    return accesstuples_manual, accesstuple2domains, skipped_rules


def _ir_access_postprocess_accesstuple2domains(
    env, accesstuples_manual, accesstuple2domains
):
    """
    Reduce accesstuple2domains to keep minimal group/domain assignments per operation,
    and remove global permissions that haven't been manually added by the user
    """
    v19_keys = set(accesstuple2domains)
    for key in list(accesstuple2domains.keys()):
        if not accesstuple2domains[key] and key not in accesstuples_manual:
            accesstuple2domains.pop(key)
            continue

        # as _ir_access_get_v19_permissions has expanded all groups, move domains up
        # the group inheritance tree to get the minimal set of permissions to add
        for group in key.group.all_implied_ids - key.group:
            group_key = (group,) + key[1:]
            if group_key not in accesstuple2domains:
                continue
            for domain in accesstuple2domains[group_key]:
                accesstuple2domains[key].pop(domain, False)

        if not accesstuple2domains[key]:
            # keep empty (=allow all) permissions only if they were added manually
            if key in accesstuples_manual:
                # set group_everyone for former ir.model.access records without group
                # if no other v19 access or rule applies to this model and operation
                if not key.group and not any(
                    model_key
                    for model_key in v19_keys
                    if model_key.model == key.model
                    and model_key.operation == key.operation
                    and model_key != key
                ):
                    group_everyone = env.ref("base.group_everyone")
                    accesstuple2domains[AccessTuple(*((group_everyone,) + key[1:]))] = (
                        accesstuple2domains.pop(key)
                    )
            else:
                accesstuple2domains.pop(key)


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


def _ir_access_create_inactive(env, vals, note):
    """
    Create an inactive ir.access record that only documents some v19 configuration
    """
    return env["ir.access"].create(
        dict(vals, active=False, note=Markup("<p>%s</p>") % note)
    )


def _ir_access_custom(env):
    """
    Create ir.access records for manually created ir.model.access and ir.rule records

    This needs evaluating all pre-migration access rules in order to not create too wide
    permissions for ir.model.access records with accompanying ir.rules and not too
    narrow ones for ir.model.access records without for some group(s).

    Do not consider interactions between v19 provisioned rules and custom rules, as the
    goal here is to just migrate the custom v19 rules, not to restore the exact
    permissions existing in v19.
    """
    accesstuples_manual, accesstuple2domains, skipped_rules = (
        _ir_access_get_v19_permissions(env)
    )
    _ir_access_postprocess_accesstuple2domains(
        env, accesstuples_manual, accesstuple2domains
    )

    DomainTuple = namedtuple("DomainTuple", ["group", "model", "domain"])
    domaintuple2operation = {}

    for accesstuple, domains in accesstuple2domains.items():
        for domain in domains or [None]:
            key = DomainTuple(accesstuple.group, accesstuple.model, domain)
            existing_operation = domaintuple2operation.get(key, "")
            domaintuple2operation[key] = "".join(
                o
                for o in "crud"
                if o == accesstuple.operation or o in existing_operation
            )

    IrAccess = env["ir.access"]

    custom_access_active = IrAccess.browse()
    custom_access_inactive = IrAccess.browse()

    for domaintuple, operation in domaintuple2operation.items():
        origins = set()
        for operation_char in operation:
            accesstuple = (domaintuple.group, domaintuple.model, operation_char)
            origins.add(accesstuple2domains[accesstuple].origin)
            origins |= accesstuple2domains[accesstuple].get(domaintuple.domain, set())
        vals = {
            "name": f"Migrated from v19 ({', '.join(sorted(origins))})",
            "operation": operation,
            "group_id": domaintuple.group.id,
            "model_id": domaintuple.model.id,
            "domain": domaintuple.domain,
        }

        try:
            with env.cr.savepoint():
                custom_access_active += IrAccess.create(vals)
        except Exception as e:  # noqa: BLE001
            openupgrade.message(
                env.cr,
                "base",
                None,
                None,
                "Creating inactive rule for %s[%s]: %s because it fails with %s",
                domaintuple.model.model,
                operation,
                domaintuple.domain,
                e,
            )
            custom_access_inactive += _ir_access_create_inactive(env, vals, e)

    for (group, model, domain, name), operations in skipped_rules.items():
        custom_access_inactive += _ir_access_create_inactive(
            env,
            {
                "name": f"Migrated from v19 ({name})",
                "operation": "".join(o for o in "crud" if o in operations),
                "group_id": group.id,
                "model_id": model.id,
                "domain": domain,
            },
            "This v19 record rule applied to a group without model access for "
            "these operations, so it has no direct equivalent in v20.",
        )

    return custom_access_active, custom_access_inactive


def _ir_access_custom_inactive(env):
    """
    Create inactive ir.access records for manually created ir.model.access and ir.rule
    records that were inactive in v19, as they are not available otherwise in v20
    """
    IrAccess = env["ir.access"]
    custom_module_filter = """
        NOT EXISTS (
            SELECT 1 FROM ir_model_data
            WHERE model=%s AND res_id=record.id
            AND module NOT IN ('__export__', '__custom__', 'studio_customization')
        )
    """
    env.cr.execute(
        f"""
        SELECT
            record.name, perm_create, perm_read, perm_write, perm_unlink, model_id,
            group_id, NULL AS domain_force
        FROM
            ir_model_access record
        JOIN
            ir_model ON ir_model.id=record.model_id
        WHERE
            NOT record.active AND {custom_module_filter}
        UNION ALL
        SELECT
            COALESCE(record.name, 'ir.rule,'||record.id), perm_create, perm_read,
            perm_write, perm_unlink, model_id, rule_group_rel.group_id, domain_force
        FROM
            ir_rule record
        JOIN
            ir_model ON ir_model.id=record.model_id
        LEFT JOIN
            rule_group_rel ON rule_group_rel.rule_group_id=record.id
        WHERE
            NOT record.active AND {custom_module_filter}
        """,
        ("ir.model.access", "ir.rule"),
    )
    result = IrAccess.browse()
    for row in env.cr.dictfetchall():
        operation = "".join(
            o for o, field_name in _operation_field_mapping.items() if row[field_name]
        )
        if not operation:
            continue
        result += _ir_access_create_inactive(
            env,
            {
                "name": f"Migrated from v19 ({row['name']})",
                "operation": operation,
                "group_id": row["group_id"],
                "model_id": row["model_id"],
                "domain": row["domain_force"],
            },
            "This record was inactive in v19.",
        )
    return result


def _ir_access_customized_rules(env):
    """
    Handle ir.rule records provided by modules that the user changed in v19, where
    they were noupdate records. In v20 they are replaced by ir.access records that are
    overwritten by the module's data.

    If the v20 record has the same role as the v19 rule (same group, the v19 standard
    domain), apply the customization the way v20 does it: deactivate the standard
    record and add a custom copy. Otherwise create an inactive record for review.
    """
    IrAccess = env["ir.access"]
    replaced = IrAccess.browse()
    deactivated = IrAccess.browse()
    review = IrAccess.browse()
    table = openupgrade.get_legacy_name("ir_rule_customized")
    if not openupgrade.table_exists(env.cr, table):
        return replaced, deactivated, review
    env.cr.execute(
        f"""
        SELECT
            customized.xmlid, customized.std_domain, customized.std_active,
            customized.diff_perms, customized.diff_groups,
            ir_rule.name, ir_rule.active, ir_rule.domain_force, ir_rule.model_id,
            ir_rule.perm_create, ir_rule.perm_read, ir_rule.perm_write,
            ir_rule.perm_unlink,
            ARRAY(
                SELECT group_id FROM rule_group_rel WHERE rule_group_id=ir_rule.id
            ) AS group_ids,
            ir_model_data.module, ir_model_data.name AS xmlid_name
        FROM
            {table} customized
        JOIN
            ir_rule ON ir_rule.id=customized.rule_id
        JOIN
            ir_model ON ir_model.id=ir_rule.model_id
        LEFT JOIN
            ir_model_data
        ON
            ir_model_data.model='ir.rule' AND ir_model_data.res_id=ir_rule.id
        ORDER BY
            customized.xmlid
        """
    )
    for row in env.cr.dictfetchall():
        operation = "".join(
            o for o, field_name in _operation_field_mapping.items() if row[field_name]
        )
        if not operation:
            continue
        group_ids = row["group_ids"]
        standard = IrAccess.browse()
        if row["module"]:
            record = env.ref(
                f"{row['module']}.{row['xmlid_name'].removesuffix('_ir_rule')}",
                raise_if_not_found=False,
            )
            if record and record._name == "ir.access":
                standard = record
        same_role = bool(
            standard
            and standard.active
            and not row["diff_perms"]
            and not row["diff_groups"]
            and len(group_ids) <= 1
            and standard.group_id.id == (group_ids[0] if group_ids else False)
            and set(standard.operation) <= set(operation)
            and _normalize_domain(standard.domain)
            == _normalize_domain(row["std_domain"])
        )
        note = escape(
            "Record rule %(xmlid)s was customized in v19. "
            "Active: %(active)s (standard: %(std_active)s). "
            "Domain: %(domain)s (standard: %(std_domain)s)."
        ) % {
            "xmlid": row["xmlid"],
            "active": row["active"],
            "std_active": row["std_active"],
            "domain": row["domain_force"] or "[]",
            "std_domain": row["std_domain"] or "[]",
        }
        if same_role and row["active"] and row["std_active"]:
            try:
                with env.cr.savepoint():
                    replaced += standard.copy(
                        {
                            "name": f"{standard.name} (customized in v19)",
                            "domain": row["domain_force"],
                            "note": Markup("<p>%s</p>") % note,
                        }
                    )
                    standard.active = False
                continue
            except Exception as e:  # noqa: BLE001
                note += escape(" Applying it in v20 failed with: %s") % e
        elif same_role and not row["active"] and row["std_active"] and not group_ids:
            standard.active = False
            deactivated += standard
            continue
        for group_id in group_ids or [False]:
            review += _ir_access_create_inactive(
                env,
                {
                    "name": f"Customized in v19 ({row['xmlid']})",
                    "operation": operation,
                    "group_id": group_id,
                    "model_id": row["model_id"],
                    "domain": row["domain_force"],
                },
                note,
            )
    return replaced, deactivated, review


def _ir_access_links(records):
    return Markup("").join(
        Markup('<li><a href="/odoo/%s/%s">%s</a></li>')
        % (record._name, record.id, record.display_name)
        for record in records
    )


def ir_access(env):
    """
    Migrate custom and customized ir.model.access and ir.rule records to ir.access and
    tell the administrators about it
    """
    custom_access_active, custom_access_inactive = _ir_access_custom(env)
    custom_access_inactive_v19 = _ir_access_custom_inactive(env)
    replaced, deactivated, review = _ir_access_customized_rules(env)

    admin_channel = "discuss.channel" in env and env.ref(
        "mail.channel_admin", raise_if_not_found=False
    )
    all_access = (
        custom_access_active
        + custom_access_inactive
        + custom_access_inactive_v19
        + replaced
        + deactivated
        + review
    )
    for access in all_access:
        openupgrade.message(
            env.cr,
            "base",
            "ir_access",
            None,
            "v19 access customization migrated to ir.access %s (%s, %s, active=%s)",
            access.id,
            access.name,
            access.model_id.model,
            access.active,
        )
    if not all_access or not admin_channel:
        return

    body = Markup(
        """
        <div class="alert alert-warning">Custom record rules and model access</div>
        <p>You have customized your model access rules.
        Note the v19 approach does not map exactly to v20, so you need to
        review and test carefully that the migrated access records for the
        following models do what you expect.</p>
        <p>Be especially cautious with group based restrictions, those will
        most likely not work the way they used to.</p>
        <p>If for example you added extra permissions with a custom ir.model.access
        record, but relied on standard ir.rules to restrict this access, this
        restriction will be gone.</p>
        <p>Also ir.model.access records without a group work as restrictions in v20.
        If you really want to grant everyone some access, you'll have to set group
        <em>Everyone</em> there. The migration only did this for models that do not
        have access restrictions set in v19.</p>
        <p>Models with custom access:</p>
        <ul>%s</ul>
        """
    ) % _ir_access_links(all_access.model_id)
    for records, text in (
        (
            custom_access_inactive,
            "Some migrated custom access records could not be activated, those "
            "have been created as inactive. Review the notes field and fix them "
            "accordingly before activating:",
        ),
        (
            custom_access_inactive_v19,
            "Custom access records that were inactive in v19 have been created "
            "as inactive records:",
        ),
        (
            replaced,
            "Standard record rules with a domain you changed in v19 have been "
            "replaced by custom access records, the standard records are inactive:",
        ),
        (
            deactivated,
            "Standard global record rules you deactivated in v19 have been "
            "deactivated:",
        ),
        (
            review,
            "Standard record rules you changed in v19 that have no direct "
            "equivalent in v20 have been created as inactive records. The standard "
            "v20 access applies until you review them:",
        ),
    ):
        if records:
            body += Markup("<p>%s</p><ul>%s</ul>") % (text, _ir_access_links(records))
    admin_channel.message_post(body=body, message_type="comment")


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.disable_invalid_filters(env)
    ir_access(env)

from odoo.tests import TransactionCase, tagged

from odoo.addons.openupgrade_framework import openupgrade_test


@tagged("-at_install", "post_install")
@openupgrade_test
class TestBaseMigration(TransactionCase):
    def _get_access(self, domain):
        return (
            self.env["ir.access"]
            .search(domain)
            .mapped(lambda x: (x.group_id, x.operation, x.domain))
        )

    def test_ir_access(self):
        """
        Test that manual ir.model.access/ir.rule records have been migrated correctly
        """
        own = "[('create_uid', '=', user.id)]"
        everything = "[(1, '=', 1)]"
        group_user = self.env.ref("base.group_user")
        group_system = self.env.ref("base.group_system")
        group_portal = self.env.ref("base.group_portal")
        self.assertItemsEqual(
            (
                (self.env["res.groups"], "d", own),
                (group_user, "cru", own),
                (group_system, "d", own),
                (self.env.ref("base.group_erp_manager"), "u", everything),
                (group_system, "ud", everything),
                (group_system, "d", False),
                (group_portal, "ru", own),
            ),
            self._get_access([("model_id.model", "=", "x_v19_base_test_model")]),
        )
        self.assertItemsEqual(
            ((group_portal, "cd", own),),
            self._get_access(
                [
                    ("model_id.model", "=", "x_v19_base_test_model"),
                    ("active", "=", False),
                ]
            ),
        )
        self.assertItemsEqual(
            ((self.env.ref("base.group_everyone"), "r", False),),
            self._get_access([("model_id.model", "=", "x_v19_base_test_model2")]),
        )

    def _skip_without_customization_data(self):
        if not self.env["res.partner.bank"].search(
            [("bank_name", "=", "OpenUpgrade v20 bank")]
        ):
            self.skipTest("data_base_migration_customization.py was not loaded")

    def test_ir_access_group_rule_restricts(self):
        """
        Test that a custom group rule keeps restricting when the group and the groups
        above it have a standard permission without domain
        """
        self._skip_without_customization_data()
        domain = "[('sequence_id', '!=', False)]"
        self.assertFalse(
            self.env.ref("base.access_ir_sequence_date_range_group_user").active
        )
        self.assertFalse(
            self.env.ref("base.access_ir_sequence_date_range_group_system").active
        )
        self.assertItemsEqual(
            (
                (self.env.ref("base.group_user"), "r", domain),
                (self.env.ref("base.group_system"), "cud", domain),
            ),
            self._get_access([("model_id.model", "=", "ir.sequence.date_range")]),
        )

    def test_ir_access_manual_access_keeps_standard_rule(self):
        """
        Test that a custom ir.model.access gets the domain of the standard group rule
        that restricted it
        """
        self._skip_without_customization_data()
        self.assertIn(
            (self.env.ref("base.group_user"), "d", "[('user_id', '=', user.id)]"),
            self._get_access([("model_id.model", "=", "res.device")]),
        )
        self.assertFalse(
            self.env["ir.access"].search(
                [
                    ("model_id.model", "=", "res.device"),
                    ("group_id", "=", self.env.ref("base.group_user").id),
                    ("domain", "=", False),
                    ("for_unlink", "=", True),
                ]
            )
        )

    def test_ir_access_global_rules(self):
        """
        Test that custom global rules stay active restrictions, with renamed fields
        and with xmlids that don't belong to a module
        """
        self._skip_without_customization_data()
        self.assertIn(
            (self.env["res.groups"], "crud", "[('account_number', '!=', 'OU20 forbidden')]"),
            self._get_access([("model_id.model", "=", "res.partner.bank")]),
        )
        self.assertIn(
            (self.env["res.groups"], "crud", "[('name', '!=', 'OU20 forbidden')]"),
            self._get_access([("model_id.model", "=", "res.partner.category")]),
        )

    def test_ir_actions_client(self):
        """
        Test that ir.actions.client#params_store has been converted
        """
        action = self.env["ir.actions.client"].search(
            [("name", "=", "Test action for params_store")]
        )
        self.assertEqual(action.params["some"], "value")

    def test_user_role_assignment(self):
        """
        Test that previous base.group_user members are regular users
        """
        user = self.env["res.users"].search([("login", "=", "test_user_v19")])
        self.assertEqual(user.role, "regular_user")
        self.assertIn(self.env.ref("base.group_user_regular"), user.group_ids)
        self.assertNotIn(
            self.env.ref("base.group_user_regular"),
            self.env.ref("base.user_admin").group_ids,
        )

    def test_ir_access_customized_rules(self):
        """
        Test that changes to ir.rule records provided by modules are carried over
        """
        IrAccess = self.env["ir.access"].with_context(active_test=False)
        self._skip_without_customization_data()
        self.assertFalse(self.env.ref("base.res_partner_bank_rule").active)
        custom_access = IrAccess.search(
            [
                ("model_id.model", "=", "res.partner.bank"),
                ("domain", "=", "[('company_id', '=', company_id)]"),
            ]
        )
        self.assertTrue(custom_access.active)
        self.assertFalse(custom_access.group_id)
        self.assertEqual(custom_access.operation, "crud")
        self.assertFalse(custom_access.is_standard)
        self.assertFalse(self.env.ref("base.res_currency_rate_rule").active)

    def test_bank_account(self):
        """
        Test that bank accounts have clearing_label_id assigned and the data of their
        bank
        """
        self.assertFalse(
            self.env["res.partner.bank"].search([("clearing_label_id", "=", False)])
        )
        account = self.env["res.partner.bank"].search(
            [("bank_name", "=", "OpenUpgrade v20 bank")]
        )
        if not account:
            self.skipTest("data_base_migration_customization.py was not loaded")
        self.assertEqual(account.account_number, "OU20 67890")
        self.assertEqual(account.bank_bic, "OUPGMXMM")
        self.assertEqual(account.city, "Monterrey")
        self.assertEqual(account.country_id, self.env.ref("base.mx"))
        self.assertEqual(
            account.clearing_label_id, self.env.ref("base.clearing_label_mx")
        )

    def test_country_zip_applicability(self):
        """
        Test that countries where the zip was not required keep it optional
        """
        if not self.env["res.partner.bank"].search(
            [("bank_name", "=", "OpenUpgrade v20 bank")]
        ):
            self.skipTest("data_base_migration_customization.py was not loaded")
        self.assertEqual(self.env.ref("base.fr").zip_applicability, "optional")

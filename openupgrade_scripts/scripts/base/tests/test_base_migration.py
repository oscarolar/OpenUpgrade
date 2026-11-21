from odoo.tests import TransactionCase, tagged

from odoo.addons.openupgrade_framework import openupgrade_test


@tagged("-at_install", "post_install")
@openupgrade_test
class TestBaseMigration(TransactionCase):
    def test_ir_access(self):
        """
        Test that manual ir.model.access/ir.rule records have been migrated correctly
        """
        expected_access = (
            (self.env["res.groups"], "r", False),
            (self.env["res.groups"], "d", "[('create_uid', '=', user.id)]"),
            (self.env.ref("base.group_user"), "cru", "[('create_uid', '=', user.id)]"),
            (self.env.ref("base.group_erp_manager"), "u", "[(1, '=', 1)]"),
            (self.env.ref("base.group_system"), "d", "[(1, '=', 1)]"),
            (self.env.ref("base.group_portal"), "ru", "[('create_uid', '=', user.id)]"),
        )
        test_model_access = self.env["ir.access"].search(
            [
                ("model_id.model", "=", "x_v19_base_test_model"),
            ]
        )
        self.assertItemsEqual(
            expected_access,
            test_model_access.mapped(lambda x: (x.group_id, x.operation, x.domain)),
        )
        expected_access2 = ((self.env.ref("base.group_everyone"), "r", False),)
        test_model_access2 = self.env["ir.access"].search(
            [
                ("model_id.model", "=", "x_v19_base_test_model2"),
            ]
        )
        self.assertItemsEqual(
            expected_access2,
            test_model_access2.mapped(lambda x: (x.group_id, x.operation, x.domain)),
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
        self.assertTrue(self.env.ref("base.res_users_rule").active)
        review_access = IrAccess.search(
            [("name", "=", "Customized in v19 (base.res_users_rule)")]
        )
        self.assertFalse(review_access.active)
        self.assertEqual(review_access.group_id, self.env.ref("base.group_system"))
        self.assertEqual(review_access.model_id.model, "res.users")

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
        self.assertEqual(account.account_number, "12345")
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
        self.assertEqual(self.env.ref("base.fr").zip_applicability, "optional")

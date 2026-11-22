from odoo.tests import TransactionCase, tagged

from odoo.addons.openupgrade_framework import openupgrade_test


@tagged("-at_install", "post_install")
@openupgrade_test
class TestBaseStatesMigration(TransactionCase):
    def setUp(self):
        super().setUp()
        if not self.env["res.partner"].search([("name", "=", "OU20 state Jeddah")]):
            self.skipTest("data_base_migration_states.py was not loaded")

    def _state_of(self, name):
        return self.env["res.partner"].search([("name", "=", name)]).state_id

    def test_partners_keep_their_merged_state(self):
        ref = self.env.ref
        self.assertEqual(self._state_of("OU20 state Jeddah"), ref("base.state_sa_002"))
        self.assertEqual(
            self._state_of("OU20 state Jeddah Industrial City"),
            ref("base.state_sa_002"),
        )
        self.assertEqual(
            self._state_of("OU20 state Riyadh delivery"), ref("base.state_sa_001")
        )
        self.assertEqual(self._state_of("OU20 state Daman"), ref("base.state_in_dn"))
        self.assertEqual(
            self._state_of("OU20 state 6th of October"), ref("base.state_eg_gz")
        )

    def test_unmerged_city_is_kept_while_used(self):
        state = self._state_of("OU20 state King Fhad")
        self.assertTrue(state)
        self.assertEqual(state.country_id, self.env.ref("base.sa"))

    def test_no_state_left_orphan(self):
        self.env.cr.execute(
            """
            SELECT COUNT(*) FROM res_partner p
            LEFT JOIN res_country_state s ON s.id = p.state_id
            WHERE p.state_id IS NOT NULL AND s.id IS NULL
            """
        )
        self.assertEqual(self.env.cr.fetchone()[0], 0)
        for xmlid in ("base.state_in_dd", "base.state_sa_40", "base.state_sa_41"):
            self.assertFalse(self.env.ref(xmlid, raise_if_not_found=False))

    def test_bank_account_state(self):
        account = self.env["res.partner.bank"].search(
            [("bank_name", "=", "OU20 Riyadh Dry Port bank")]
        )
        if account:
            self.assertEqual(account.state_id, self.env.ref("base.state_sa_001"))

    def test_fiscal_position_states(self):
        position = self.env["account.fiscal.position"].search(
            [("name", "=", "OU20 Mecca cities")]
        )
        self.assertEqual(position.state_ids, self.env.ref("base.state_sa_002"))

    def test_l10n_states_moved_to_base(self):
        position = self.env["account.fiscal.position"].search(
            [("name", "=", "OU20 Gulf states")]
        )
        if not position:
            self.skipTest("l10n_om, l10n_bh or l10n_lb_account was not installed")
        ref = self.env.ref
        self.assertEqual(
            position.state_ids,
            ref("base.state_om_ma") | ref("base.state_bh_13") | ref("base.state_lb_ba"),
        )
        self.assertEqual(self._state_of("OU20 state Muscat"), ref("base.state_om_ma"))
        self.assertEqual(
            self._state_of("OU20 state Beirut arabic"), ref("base.state_lb_ba")
        )
        for code in ("om", "bh", "lb"):
            states = self.env["res.country.state"].search(
                [("country_id", "=", ref(f"base.{code}").id)]
            )
            self.assertFalse(states.filtered(lambda state: "-" not in state.code), code)

    def test_default_state(self):
        default = self.env["ir.default"].search(
            [
                ("field_id.model", "=", "res.partner"),
                ("field_id.name", "=", "state_id"),
                ("user_id", "=", self.env.ref("base.user_admin").id),
            ]
        )
        self.assertEqual(len(default), 1)
        self.assertEqual(int(default.json_value), self.env.ref("base.state_sa_002").id)

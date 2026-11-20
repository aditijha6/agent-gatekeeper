"""
Automated tests for the Agent Gatekeeper.

Run from the project folder:   python -m unittest -v
TC1-TC6 are the six main test cases (also listed in TEST_CASES.md).
The extra tests check the remaining rules and the revocation proof.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gatekeeper as gk  # noqa: E402
from storage import Store  # noqa: E402

DAY = "2026-11-20"


class GatekeeperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(os.path.join(self.tmp.name, "test.db"))
        self.store.register_agent("C1001", "BudgetBot", when=f"{DAY} 09:00:00")
        self.store.register_agent("C1001", "ShopperGPT", when=f"{DAY} 09:01:00")
        self.store.revoke_agent("C1001", "ShopperGPT", when=f"{DAY} 09:02:00")

    def tearDown(self):
        self.store.conn.close()
        self.tmp.cleanup()

    def check(self, customer, agent, action, amount, time="10:00:00"):
        result, _ = self.store.check_request(customer, agent, action, amount,
                                             when=f"{DAY} {time}")
        return result

    # ---------- six main test cases ----------

    def test_TC1_unknown_agent_is_blocked(self):
        r = self.check("C1001", "RogueBot", "view_balance", "")
        self.assertEqual((r.decision, r.rule), (gk.BLOCK, 1))

    def test_TC2_revoked_agent_is_blocked_even_for_read_only(self):
        r = self.check("C1001", "ShopperGPT", "view_balance", "")
        self.assertEqual((r.decision, r.rule), (gk.BLOCK, 2))

    def test_TC3_view_balance_is_allowed(self):
        r = self.check("C1001", "BudgetBot", "view_balance", "")
        self.assertEqual((r.decision, r.rule), (gk.ALLOW, 4))

    def test_TC4_small_bill_is_allowed(self):
        r = self.check("C1001", "BudgetBot", "pay_bill", "120")
        self.assertEqual((r.decision, r.rule), (gk.ALLOW, 8))

    def test_TC5_big_bill_asks_customer(self):
        r = self.check("C1001", "BudgetBot", "pay_bill", "750")
        self.assertEqual((r.decision, r.rule), (gk.ASK, 7))

    def test_TC6_transfer_asks_customer(self):
        r = self.check("C1001", "BudgetBot", "transfer_money", "50")
        self.assertEqual((r.decision, r.rule), (gk.ASK, 7))

    # ---------- extra checks ----------

    def test_unsupported_action_is_blocked(self):
        r = self.check("C1001", "BudgetBot", "close_account", "")
        self.assertEqual((r.decision, r.rule), (gk.BLOCK, 3))

    def test_bad_amounts_are_blocked(self):
        for bad in ["", "-20", "0", "abc", "nan"]:
            r = self.check("C1001", "BudgetBot", "pay_bill", bad)
            self.assertEqual((r.decision, r.rule), (gk.BLOCK, 5), msg=bad)

    def test_daily_cap_blocks_after_2000(self):
        for t in ["10:00:00", "10:01:00", "10:02:00", "10:03:00"]:
            r = self.check("C1001", "BudgetBot", "pay_bill", "450", time=t)
            self.assertEqual(r.decision, gk.ALLOW)          # 4 x 450 = 1,800 allowed
        r = self.check("C1001", "BudgetBot", "pay_bill", "300", time="10:04:00")
        self.assertEqual((r.decision, r.rule), (gk.BLOCK, 6))   # 2,100 > 2,000

    def test_agent_is_registered_per_customer(self):
        r = self.check("C1002", "BudgetBot", "view_balance", "")   # registered for C1001 only
        self.assertEqual((r.decision, r.rule), (gk.BLOCK, 1))

    def test_names_are_not_case_sensitive(self):
        r = self.check("c1001", "budgetbot", "view_balance", "")
        self.assertEqual(r.decision, gk.ALLOW)

    def test_revocation_time_is_saved_as_proof(self):
        row = self.store._find_agent("C1001", "ShopperGPT")
        self.assertEqual(row["revoked_at"], f"{DAY} 09:02:00")
        events = [r["event"] for r in self.store.audit_rows()]
        self.assertIn("REVOKE", events)

    def test_revoked_agent_cannot_be_reregistered(self):
        ok, _ = self.store.register_agent("C1001", "ShopperGPT")
        self.assertFalse(ok)
        self.assertEqual(self.store.agent_status("C1001", "ShopperGPT"), "revoked")

    def test_every_request_is_logged(self):
        self.check("C1001", "BudgetBot", "pay_bill", "120")
        last = self.store.audit_rows(1)[0]
        self.assertEqual((last["event"], last["decision"], last["rule"]),
                         ("REQUEST", gk.ALLOW, 8))
        self.assertTrue(last["logged_at"].startswith(DAY))


if __name__ == "__main__":
    unittest.main(verbosity=2)

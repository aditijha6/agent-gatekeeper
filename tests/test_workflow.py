"""
Tests for the customer-approval workflow, permissions, audit log and CSV export.

Run from the project folder:   python -m unittest -v
The numbers W1-W16 match the 16 required checks listed in TEST_CASES.md.
The original 14 tests are unchanged in test_gatekeeper.py.
"""

import csv
import io
import os
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.parse
import urllib.request
from http.server import HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gatekeeper as gk  # noqa: E402
from storage import Store, request_label  # noqa: E402

DAY = "2026-11-20"


def at(time):
    return f"{DAY} {time}"


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(os.path.join(self.tmp.name, "test.db"))
        self.store.register_agent("C1001", "BudgetBot", when=at("09:00:00"))
        self.store.register_agent("C1001", "ShopperGPT", when=at("09:01:00"))
        self.store.revoke_agent("C1001", "ShopperGPT", when=at("09:02:00"))
        self.store.register_agent("C1002", "FinanceBuddy", permissions={"view_balance"},
                                  when=at("09:03:00"))

    def tearDown(self):
        self.store.conn.close()
        self.tmp.cleanup()

    def request(self, action, amount, agent="BudgetBot", customer="C1001", time="10:00:00"):
        return self.store.check_request(customer, agent, action, amount, when=at(time))

    def status(self, tx):
        return self.store.get_transaction(tx["id"])["status"]

    # ---------- W1-W4: basic decisions ----------

    def test_W01_unknown_agent_blocked(self):
        r, tx = self.request("view_balance", "", agent="RogueBot")
        self.assertEqual((r.decision, r.rule, tx["status"]), (gk.BLOCK, 1, gk.BLOCKED))

    def test_W01b_unknown_customer_blocked(self):
        r, _ = self.request("view_balance", "", customer="C9999")
        self.assertEqual((r.decision, r.rule), (gk.BLOCK, 1))

    def test_W02_revoked_agent_blocked(self):
        r, tx = self.request("pay_bill", "10", agent="ShopperGPT")
        self.assertEqual((r.decision, r.rule, tx["status"]), (gk.BLOCK, 2, gk.BLOCKED))

    def test_W03_authorized_balance_enquiry_allowed(self):
        r, tx = self.request("view_balance", "", agent="FinanceBuddy", customer="C1002")
        self.assertEqual((r.decision, r.rule, tx["status"]), (gk.ALLOW, 4, gk.ALLOWED))

    def test_W03b_action_without_permission_blocked(self):
        r, _ = self.request("pay_bill", "20", agent="FinanceBuddy", customer="C1002")
        self.assertEqual((r.decision, r.rule), (gk.BLOCK, 3))
        self.assertIn("permission", r.reason)

    def test_W04_small_permitted_payment_allowed(self):
        r, tx = self.request("pay_bill", "120")
        self.assertEqual((r.decision, r.rule, tx["status"]), (gk.ALLOW, 8, gk.ALLOWED))

    # ---------- W5-W7: the approval workflow ----------

    def test_W05_consent_needed_becomes_pending(self):
        r, tx = self.request("transfer_money", "300")
        self.assertEqual((r.decision, r.rule, tx["status"]), (gk.ASK, 7, gk.PENDING))
        self.assertIsNone(tx["decided_at"])
        self.assertEqual([t["id"] for t in self.store.pending_transactions()], [tx["id"]])

    def test_W06_customer_approval_sets_approved(self):
        _, tx = self.request("pay_bill", "750")
        ok, msg = self.store.customer_decision(request_label(tx["id"]), "C1001", "1111",
                                               approve=True, when=at("10:05:00"))
        self.assertTrue(ok, msg)
        row = self.store.get_transaction(tx["id"])
        self.assertEqual((row["status"], row["decided_at"], row["decided_by"]),
                         (gk.APPROVED, at("10:05:00"), "customer C1001"))
        self.assertEqual(self.store.pending_transactions(), [])

    def test_W07_customer_rejection_sets_rejected(self):
        _, tx = self.request("transfer_money", "50")
        ok, msg = self.store.customer_decision(tx["id"], "C1001", "1111", approve=False,
                                               when=at("10:06:00"))
        self.assertTrue(ok, msg)
        row = self.store.get_transaction(tx["id"])
        self.assertEqual((row["status"], row["decided_at"]), (gk.REJECTED, at("10:06:00")))

    # ---------- W8-W9: only completed payments count ----------

    def test_W08_pending_not_counted_as_completed(self):
        self.request("transfer_money", "1900")
        self.assertEqual(self.store.spent_today("C1001", "BudgetBot", DAY), 0.0)
        r, _ = self.request("pay_bill", "450", time="10:01:00")   # still fits under the cap
        self.assertEqual(r.decision, gk.ALLOW)

    def test_W09_rejected_not_counted_as_completed(self):
        _, tx = self.request("pay_bill", "900")
        self.store.customer_decision(tx["id"], "C1001", "1111", approve=False, when=at("10:02:00"))
        self.assertEqual(self.store.spent_today("C1001", "BudgetBot", DAY), 0.0)
        _, tx2 = self.request("pay_bill", "700", time="10:03:00")
        self.store.customer_decision(tx2["id"], "C1001", "1111", approve=True, when=at("10:04:00"))
        self.assertEqual(self.store.spent_today("C1001", "BudgetBot", DAY), 700.0)

    # ---------- W10-W11: no double or unauthorized decisions ----------

    def test_W10_duplicate_approval_prevented(self):
        _, tx = self.request("pay_bill", "750")
        ok1, _ = self.store.customer_decision(tx["id"], "C1001", "1111", True, when=at("10:05:00"))
        ok2, msg2 = self.store.customer_decision(tx["id"], "C1001", "1111", True, when=at("10:06:00"))
        ok3, _ = self.store.customer_decision(tx["id"], "C1001", "1111", False, when=at("10:07:00"))
        self.assertTrue(ok1)
        self.assertFalse(ok2)
        self.assertFalse(ok3)
        self.assertIn("cannot be decided twice", msg2)
        row = self.store.get_transaction(tx["id"])
        self.assertEqual((row["status"], row["decided_at"]), (gk.APPROVED, at("10:05:00")))
        self.assertEqual(self.store.spent_today("C1001", "BudgetBot", DAY), 750.0)  # counted once

    def test_W11_unauthorized_approval_prevented(self):
        _, tx = self.request("transfer_money", "100")
        # wrong PIN
        self.assertFalse(self.store.customer_decision(tx["id"], "C1001", "9999", True)[0])
        # another customer, even with their own correct PIN
        self.assertFalse(self.store.customer_decision(tx["id"], "C1002", "2222", True)[0])
        # no PIN at all
        self.assertFalse(self.store.customer_decision(tx["id"], "C1001", "", True)[0])
        self.assertEqual(self.status(tx), gk.PENDING)
        # an agent cannot "approve" through the request channel
        r, _ = self.request("approve", "", time="10:01:00")
        self.assertEqual((r.decision, r.rule), (gk.BLOCK, 3))
        refused = [a for a in self.store.audit_rows() if a["event"] == "APPROVAL_REFUSED"]
        self.assertEqual(len(refused), 3)

    def test_W11b_revoking_agent_rejects_its_pending_transactions(self):
        _, tx = self.request("transfer_money", "100")
        ok, msg = self.store.revoke_agent("C1001", "BudgetBot", when=at("10:10:00"))
        self.assertTrue(ok)
        self.assertIn("1 pending", msg)
        self.assertEqual(self.status(tx), gk.REJECTED)
        self.assertFalse(self.store.customer_decision(tx["id"], "C1001", "1111", True)[0])

    # ---------- W12-W14: amounts, cap, actions ----------

    def test_W12_invalid_amounts_blocked(self):
        for bad in ["", "-5", "0", "ten", "inf", "1e400"]:
            r, tx = self.request("transfer_money", bad)
            self.assertEqual((r.decision, r.rule, tx["status"]), (gk.BLOCK, 5, gk.BLOCKED), msg=bad)

    def test_W13_daily_cap_enforced_on_request_and_on_approval(self):
        r, _ = self.request("transfer_money", "2500")                  # alone above the cap
        self.assertEqual((r.decision, r.rule), (gk.BLOCK, 6))
        _, t1 = self.request("transfer_money", "1500", time="10:01:00")
        _, t2 = self.request("transfer_money", "1000", time="10:02:00")
        self.assertTrue(self.store.customer_decision(t1["id"], "C1001", "1111", True, when=at("10:03:00"))[0])
        ok, msg = self.store.customer_decision(t2["id"], "C1001", "1111", True, when=at("10:04:00"))
        self.assertFalse(ok)                                          # 1,500 + 1,000 > 2,000
        self.assertEqual(self.status(t2), gk.BLOCKED)
        self.assertEqual(self.store.spent_today("C1001", "BudgetBot", DAY), 1500.0)

    def test_W14_unsupported_action_blocked(self):
        r, tx = self.request("close_account", "")
        self.assertEqual((r.decision, r.rule, tx["status"]), (gk.BLOCK, 3, gk.BLOCKED))

    # ---------- W15-W16: audit log and CSV ----------

    def test_W15_audit_log_reflects_decisions(self):
        _, tx = self.request("pay_bill", "750")
        self.store.customer_decision(tx["id"], "C1001", "1111", True, when=at("10:05:00"))
        label = request_label(tx["id"])
        rows = [r for r in self.store.audit_rows() if r["request_id"] == label]
        by_event = {r["event"]: r for r in rows}
        self.assertEqual(by_event["REQUEST"]["status"], gk.PENDING)
        self.assertEqual(by_event["REQUEST"]["customer_decision"], "AWAITING")
        d = by_event["CUSTOMER_DECISION"]
        self.assertEqual((d["status"], d["customer_decision"], d["decided_at"], d["rule"]),
                         (gk.APPROVED, "APPROVE", at("10:05:00"), 7))
        self.assertEqual(d["agent_id"], self.store._find_agent("C1001", "BudgetBot")["id"])

    def test_W16_csv_exports_show_real_statuses(self):
        self.request("pay_bill", "100")                                    # ALLOWED
        self.request("view_balance", "", agent="RogueBot")                 # BLOCKED
        _, a = self.request("pay_bill", "750")
        _, b = self.request("transfer_money", "40")
        self.request("transfer_money", "60")                               # stays PENDING
        self.store.customer_decision(a["id"], "C1001", "1111", True)
        self.store.customer_decision(b["id"], "C1001", "1111", False)
        tx_rows = list(csv.DictReader(io.StringIO(self.store.export_transactions_csv())))
        self.assertEqual([r["status"] for r in tx_rows],
                         [gk.ALLOWED, gk.BLOCKED, gk.APPROVED, gk.REJECTED, gk.PENDING])
        self.assertEqual(tx_rows[2]["request_id"], request_label(a["id"]))
        audit = list(csv.DictReader(io.StringIO(self.store.export_audit_csv())))
        statuses = {r["status"] for r in audit if r["status"]}
        self.assertTrue({gk.ALLOWED, gk.BLOCKED, gk.PENDING, gk.APPROVED, gk.REJECTED} <= statuses)

    # ---------- other safety checks ----------

    def test_register_for_unknown_customer_refused(self):
        ok, _ = self.store.register_agent("C9999", "Bot")
        self.assertFalse(ok)

    def test_update_permissions(self):
        ok, _ = self.store.update_permissions("C1002", "FinanceBuddy", {"view_balance", "pay_bill"})
        self.assertTrue(ok)
        r, _ = self.request("pay_bill", "20", agent="FinanceBuddy", customer="C1002")
        self.assertEqual(r.decision, gk.ALLOW)
        self.assertFalse(self.store.update_permissions("C1001", "ShopperGPT", {"view_balance"})[0])

    def test_reset_needs_typed_confirmation(self):
        ok, _ = self.store.reset("")
        self.assertFalse(ok)
        self.assertEqual(len(self.store.list_agents()), 3)
        ok, _ = self.store.reset("RESET")
        self.assertTrue(ok)
        self.assertEqual(len(self.store.list_agents()), 0)
        self.assertEqual(len(self.store.list_customers()), 3)

    def test_pins_are_not_stored_in_plain_text(self):
        row = self.store.get_customer("C1001")
        self.assertNotEqual(row["pin_hash"], "1111")
        self.assertEqual(len(row["pin_hash"]), 64)


class OldDatabaseUpgradeTest(unittest.TestCase):
    """A database made by the first version must open without losing anything."""

    def test_old_database_is_upgraded_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "old.db")
            conn = sqlite3.connect(path)
            conn.executescript("""
                CREATE TABLE agents (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer TEXT NOT NULL COLLATE NOCASE, agent_name TEXT NOT NULL COLLATE NOCASE,
                    registered_at TEXT NOT NULL, revoked_at TEXT, UNIQUE (customer, agent_name));
                CREATE TABLE audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, logged_at TEXT NOT NULL,
                    event TEXT NOT NULL, customer TEXT, agent_name TEXT, action TEXT, amount REAL,
                    decision TEXT, rule INTEGER, reason TEXT);
                INSERT INTO agents (customer, agent_name, registered_at) VALUES ('C1001', 'OldBot', '2026-11-19 10:00:00');
                INSERT INTO agents (customer, agent_name, registered_at, revoked_at)
                    VALUES ('C1001', 'GoneBot', '2026-11-19 10:00:00', '2026-11-19 11:00:00');
                INSERT INTO audit_log (logged_at, event, customer, agent_name, reason)
                    VALUES ('2026-11-19 11:00:00', 'REVOKE', 'C1001', 'GoneBot', 'proof');
            """)
            conn.commit()
            conn.close()

            store = Store(path)
            self.assertEqual(store._find_agent("C1001", "GoneBot")["revoked_at"], "2026-11-19 11:00:00")
            self.assertEqual(len(store.audit_rows()), 1)                      # old proof kept
            self.assertEqual(gk.parse_permissions(store._find_agent("C1001", "OldBot")["permissions"]),
                             gk.ALL_ACTIONS)                                  # old agents keep full access
            r, _ = store.check_request("C1001", "OldBot", "pay_bill", "50")
            self.assertEqual(r.decision, gk.ALLOW)
            store.conn.close()


class WebAppEndToEndTest(unittest.TestCase):
    """Starts the real web server and clicks through approve / reject over HTTP."""

    def setUp(self):
        import app
        self.app = app
        self.tmp = tempfile.TemporaryDirectory()
        app.STORE = Store(os.path.join(self.tmp.name, "web.db"))
        app.STORE.load_demo_data()
        self.server = HTTPServer(("127.0.0.1", 0), app.Handler)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.app.STORE.conn.close()
        self.tmp.cleanup()

    def post(self, path, **fields):
        data = urllib.parse.urlencode(fields).encode()
        with urllib.request.urlopen(self.base + path, data=data) as resp:   # follows the redirect
            return resp.read().decode()

    def get(self, path):
        with urllib.request.urlopen(self.base + path) as resp:
            return resp.read().decode()

    def test_approve_and_reject_through_the_website(self):
        page = self.post("/check", customer="C1001", agent="BudgetBot", action="pay_bill", amount="750")
        self.assertIn("PENDING", page)
        self.assertIn("TX-0001", page)
        page = self.post("/decision", tx="TX-0001", customer="C1001", pin="0000", choice="approve")
        self.assertIn("Wrong PIN", page)
        page = self.post("/decision", tx="TX-0001", customer="C1001", pin="1111", choice="approve")
        self.assertIn("TX-0001 APPROVED", page)
        self.post("/check", customer="C1001", agent="BudgetBot", action="transfer_money", amount="40")
        page = self.post("/decision", tx="TX-0002", customer="C1001", pin="1111", choice="reject")
        self.assertIn("TX-0002 REJECTED", page)
        csv_text = self.get("/transactions.csv")
        self.assertIn("TX-0001", csv_text)
        self.assertIn("APPROVED", csv_text)
        self.assertIn("REJECTED", csv_text)
        self.assertIn("CUSTOMER_DECISION", self.get("/audit.csv"))
        self.assertIn("PGD202571184", self.get("/"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

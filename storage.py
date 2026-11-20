"""
Storage for the Agent Gatekeeper, using SQLite (a database in a single file,
built into Python - nothing to install).

Two tables:
  agents     - every registered agent, with registered_at and revoked_at
  audit_log  - every request, decision, registration and revocation,
               with the date and time
"""

import csv
import io
import sqlite3
from datetime import datetime

import gatekeeper as gk

AUDIT_COLUMNS = ["id", "logged_at", "event", "customer", "agent_name",
                 "action", "amount", "decision", "rule", "reason"]


def now_text():
    """Current local date and time, e.g. '2026-11-20 18:05:42'."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Store:
    def __init__(self, path="gatekeeper.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS agents (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                customer      TEXT NOT NULL COLLATE NOCASE,
                agent_name    TEXT NOT NULL COLLATE NOCASE,
                registered_at TEXT NOT NULL,
                revoked_at    TEXT,
                UNIQUE (customer, agent_name)
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                logged_at  TEXT NOT NULL,
                event      TEXT NOT NULL,      -- REQUEST, REGISTER or REVOKE
                customer   TEXT,
                agent_name TEXT,
                action     TEXT,
                amount     REAL,
                decision   TEXT,
                rule       INTEGER,
                reason     TEXT
            );
        """)
        self.conn.commit()

    # ---------- helpers ----------

    def _find_agent(self, customer, agent_name):
        return self.conn.execute(
            "SELECT * FROM agents WHERE customer = ? AND agent_name = ?",
            (customer, agent_name)).fetchone()

    def agent_status(self, customer, agent_name):
        """Return 'unknown', 'active' or 'revoked'."""
        row = self._find_agent(customer, agent_name)
        if row is None:
            return "unknown"
        return "revoked" if row["revoked_at"] else "active"

    def spent_today(self, customer, agent_name, day):
        """Total money this agent moved on `day` (YYYY-MM-DD) with ALLOW decisions."""
        row = self.conn.execute(
            """SELECT COALESCE(SUM(amount), 0) AS total FROM audit_log
               WHERE event = 'REQUEST' AND decision = ?
                 AND action IN ('pay_bill', 'transfer_money')
                 AND customer = ? COLLATE NOCASE
                 AND agent_name = ? COLLATE NOCASE
                 AND logged_at LIKE ?""",
            (gk.ALLOW, customer, agent_name, day + "%")).fetchone()
        return float(row["total"])

    def _log(self, when, event, customer, agent_name, action=None,
             amount=None, decision=None, rule=None, reason=None):
        self.conn.execute(
            """INSERT INTO audit_log (logged_at, event, customer, agent_name,
                                      action, amount, decision, rule, reason)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (when, event, customer, agent_name, action, amount,
             decision, rule, reason))
        self.conn.commit()

    # ---------- main features ----------

    def check_request(self, customer, agent_name, action, amount_text, when=None):
        """Decide on one agent request, save it in the audit log, return (Decision, time)."""
        when = when or now_text()
        customer = (customer or "").strip()
        agent_name = (agent_name or "").strip()
        action = (action or "").strip()
        amount = gk.parse_amount(amount_text)

        status = self.agent_status(customer, agent_name)
        spent = self.spent_today(customer, agent_name, when[:10])
        result = gk.decide(status, action, amount, spent)

        self._log(when, "REQUEST", customer, agent_name, action, amount,
                  result.decision, result.rule, result.reason)
        return result, when

    def register_agent(self, customer, agent_name, when=None):
        """Register an agent for a customer. Returns (ok, message)."""
        when = when or now_text()
        customer = (customer or "").strip()
        agent_name = (agent_name or "").strip()
        if not customer or not agent_name:
            return False, "Enter both a customer ID and an agent name."
        if len(customer) > 60 or len(agent_name) > 60:
            return False, "Customer ID and agent name must be 60 characters or fewer."

        row = self._find_agent(customer, agent_name)
        if row is not None and row["revoked_at"]:
            return False, (f"'{agent_name}' was revoked for {customer} on "
                           f"{row['revoked_at']}. A revoked agent stays blocked; "
                           f"register it under a new name if the customer trusts it again.")
        if row is not None:
            return False, (f"'{agent_name}' is already registered for {customer} "
                           f"(since {row['registered_at']}).")

        self.conn.execute(
            "INSERT INTO agents (customer, agent_name, registered_at) VALUES (?, ?, ?)",
            (customer, agent_name, when))
        self._log(when, "REGISTER", customer, agent_name,
                  reason=f"Agent registered at {when}.")
        return True, f"Registered '{agent_name}' for {customer} at {when}."

    def revoke_agent(self, customer, agent_name, when=None):
        """Revoke an agent and save the date and time as proof. Returns (ok, message)."""
        when = when or now_text()
        customer = (customer or "").strip()
        agent_name = (agent_name or "").strip()

        row = self._find_agent(customer, agent_name)
        if row is None:
            return False, f"No agent called '{agent_name}' is registered for {customer}."
        if row["revoked_at"]:
            return False, f"'{agent_name}' was already revoked on {row['revoked_at']}."

        self.conn.execute("UPDATE agents SET revoked_at = ? WHERE id = ?",
                          (when, row["id"]))
        self._log(when, "REVOKE", customer, agent_name,
                  reason=f"Access revoked at {when}. This entry is the proof of revocation.")
        return True, (f"Revoked '{agent_name}' for {customer} at {when}. "
                      f"The date and time are saved as proof.")

    # ---------- reading data for the screen ----------

    def list_agents(self):
        return self.conn.execute(
            "SELECT * FROM agents ORDER BY id DESC").fetchall()

    def audit_rows(self, limit=200):
        return self.conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def export_csv(self):
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(AUDIT_COLUMNS)
        for row in self.conn.execute("SELECT * FROM audit_log ORDER BY id"):
            writer.writerow([row[c] for c in AUDIT_COLUMNS])
        return out.getvalue()

    # ---------- demo helpers ----------

    def load_demo_data(self):
        """Sample agents so the test cases can be run straight away."""
        self.register_agent("C1001", "BudgetBot")
        self.register_agent("C1001", "ShopperGPT")
        self.revoke_agent("C1001", "ShopperGPT")
        self.register_agent("C1002", "FinanceBuddy")

    def reset(self):
        self.conn.execute("DELETE FROM agents")
        self.conn.execute("DELETE FROM audit_log")
        self.conn.commit()

"""
Storage for the Agent Gatekeeper, using SQLite (a database in a single file,
built into Python - nothing to install).

Tables
  customers     - demo bank customers and a hashed approval PIN for each
  agents        - every registered agent: permissions, registered_at, revoked_at
  transactions  - every agent request with its status:
                  ALLOWED, BLOCKED, PENDING, APPROVED or REJECTED
  audit_log     - append-only history of every event (requests, customer
                  decisions, registrations, permission changes, revocations,
                  refused approval attempts). Rows are never edited.

Older database files (from the first version of this project) are upgraded
automatically: missing columns/tables are added, nothing is deleted.
"""

import csv
import hashlib
import io
import os
import sqlite3
from datetime import datetime

import gatekeeper as gk

AUDIT_COLUMNS = ["id", "logged_at", "event", "request_id", "customer", "agent_id",
                 "agent_name", "action", "amount", "rule", "decision", "status",
                 "customer_decision", "decided_at", "reason"]
TRANSACTION_COLUMNS = ["request_id", "created_at", "customer", "agent_id", "agent_name",
                       "action", "amount", "rule", "decision", "status", "reason",
                       "decided_at", "decided_by"]

# Demo customers for the prototype (fictional people). PINs are stored hashed.
DEMO_CUSTOMERS = [
    ("C1001", "Asha Verma", "1111"),
    ("C1002", "Rahul Mehta", "2222"),
    ("C1003", "Neha Kapoor", "3333"),
]
ALL_PERMISSIONS = ",".join(sorted(gk.ALL_ACTIONS))


def now_text():
    """Current local date and time, e.g. '2026-11-20 18:05:42'."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def request_label(tx_id):
    """Transaction number shown to people, e.g. 7 -> 'TX-0007'."""
    return f"TX-{int(tx_id):04d}"


def parse_request_label(text):
    """'TX-0007', 'tx-7' or '7' -> 7; anything else -> None."""
    t = str(text or "").strip().upper().replace("TX-", "")
    return int(t) if t.isdigit() else None


def _hash_pin(pin, salt_hex):
    return hashlib.pbkdf2_hmac("sha256", str(pin).encode("utf-8"),
                               bytes.fromhex(salt_hex), 20000).hex()


class Store:
    def __init__(self, path="gatekeeper.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY COLLATE NOCASE,
                name        TEXT NOT NULL,
                pin_salt    TEXT,
                pin_hash    TEXT,
                created_at  TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS agents (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                customer      TEXT NOT NULL COLLATE NOCASE,
                agent_name    TEXT NOT NULL COLLATE NOCASE,
                registered_at TEXT NOT NULL,
                revoked_at    TEXT,
                UNIQUE (customer, agent_name)
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                customer   TEXT,
                agent_id   INTEGER,
                agent_name TEXT,
                action     TEXT,
                amount     REAL,
                rule       INTEGER,
                decision   TEXT NOT NULL,
                status     TEXT NOT NULL,
                reason     TEXT,
                decided_at TEXT,
                decided_by TEXT
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                logged_at  TEXT NOT NULL,
                event      TEXT NOT NULL,
                customer   TEXT,
                agent_name TEXT,
                action     TEXT,
                amount     REAL,
                decision   TEXT,
                rule       INTEGER,
                reason     TEXT
            );
        """)
        # Safe upgrade of databases made by the first version (adds columns only).
        self._add_missing_columns("agents", {
            "permissions": f"TEXT NOT NULL DEFAULT '{ALL_PERMISSIONS}'"})
        self._add_missing_columns("audit_log", {
            "request_id": "TEXT", "agent_id": "INTEGER", "status": "TEXT",
            "customer_decision": "TEXT", "decided_at": "TEXT"})
        self._seed_customers()
        self.conn.commit()

    # ---------- setup helpers ----------

    def _add_missing_columns(self, table, columns):
        existing = {r["name"] for r in self.conn.execute(f"PRAGMA table_info({table})")}
        for name, declaration in columns.items():
            if name not in existing:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")

    def _seed_customers(self):
        when = now_text()
        for cid, name, pin in DEMO_CUSTOMERS:
            if self.get_customer(cid) is None:
                salt = os.urandom(16).hex()
                self.conn.execute(
                    "INSERT INTO customers VALUES (?, ?, ?, ?, ?)",
                    (cid, name, salt, _hash_pin(pin, salt), when))
        # Customers that only exist in an old database's agents table are kept,
        # but have no PIN, so nobody can approve payments for them.
        for row in self.conn.execute("SELECT DISTINCT customer FROM agents").fetchall():
            if self.get_customer(row["customer"]) is None:
                self.conn.execute(
                    "INSERT INTO customers VALUES (?, ?, NULL, NULL, ?)",
                    (row["customer"], "(from older data, no PIN)", when))

    # ---------- look-ups ----------

    def get_customer(self, customer_id):
        return self.conn.execute("SELECT * FROM customers WHERE customer_id = ?",
                                 (customer_id,)).fetchone()

    def _find_agent(self, customer, agent_name):
        return self.conn.execute(
            "SELECT * FROM agents WHERE customer = ? AND agent_name = ?",
            (customer, agent_name)).fetchone()

    def agent_status(self, customer, agent_name):
        """Return 'unknown', 'active' or 'revoked'."""
        if self.get_customer(customer) is None:
            return "unknown"
        row = self._find_agent(customer, agent_name)
        if row is None:
            return "unknown"
        return "revoked" if row["revoked_at"] else "active"

    def get_transaction(self, tx_id):
        return self.conn.execute("SELECT * FROM transactions WHERE id = ?",
                                 (tx_id,)).fetchone()

    def spent_today(self, customer, agent_name, day):
        """
        Money this agent COMPLETED for this customer on `day` (YYYY-MM-DD):
        ALLOWED payments made that day plus APPROVED payments approved that day.
        PENDING, REJECTED and BLOCKED transactions never count.
        """
        row = self.conn.execute(
            """SELECT COALESCE(SUM(amount), 0) AS total FROM transactions
               WHERE customer = ? COLLATE NOCASE AND agent_name = ? COLLATE NOCASE
                 AND action IN ('pay_bill', 'transfer_money')
                 AND ((status = ? AND created_at LIKE ?)
                   OR (status = ? AND decided_at LIKE ?))""",
            (customer, agent_name, gk.ALLOWED, day + "%", gk.APPROVED, day + "%")
        ).fetchone()
        return float(row["total"])

    def _log(self, when, event, customer=None, agent_name=None, action=None,
             amount=None, decision=None, rule=None, reason=None, request_id=None,
             agent_id=None, status=None, customer_decision=None, decided_at=None):
        self.conn.execute(
            """INSERT INTO audit_log (logged_at, event, request_id, customer, agent_id,
                   agent_name, action, amount, rule, decision, status,
                   customer_decision, decided_at, reason)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (when, event, request_id, customer, agent_id, agent_name, action, amount,
             rule, decision, status, customer_decision, decided_at, reason))

    # ---------- agent requests ----------

    def check_request(self, customer, agent_name, action, amount_text, when=None):
        """
        Decide on one agent request. Saves it as a transaction (ALLOWED,
        BLOCKED or PENDING) and in the audit log. Returns (Decision, transaction row).
        """
        when = when or now_text()
        customer = (customer or "").strip()
        agent_name = (agent_name or "").strip()
        action = (action or "").strip()
        amount = gk.parse_amount(amount_text)

        status = self.agent_status(customer, agent_name)
        agent = self._find_agent(customer, agent_name) if status != "unknown" else None
        permissions = gk.parse_permissions(agent["permissions"]) if agent else None
        spent = self.spent_today(customer, agent_name, when[:10])
        result = gk.decide(status, action, amount, spent, permissions)

        cur = self.conn.execute(
            """INSERT INTO transactions (created_at, customer, agent_id, agent_name, action,
                   amount, rule, decision, status, reason)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (when, customer, agent["id"] if agent else None, agent_name, action, amount,
             result.rule, result.decision, result.status, result.reason))
        tx_id = cur.lastrowid
        self._log(when, "REQUEST", customer, agent_name, action, amount,
                  result.decision, result.rule, result.reason,
                  request_id=request_label(tx_id),
                  agent_id=agent["id"] if agent else None, status=result.status,
                  customer_decision="AWAITING" if result.status == gk.PENDING else None)
        self.conn.commit()
        return result, self.get_transaction(tx_id)

    # ---------- the customer's approval ----------

    def customer_decision(self, tx_ref, customer_id, pin, approve, when=None):
        """
        The CUSTOMER approves or rejects a PENDING transaction.
        Only the customer who owns the transaction, with the right PIN, can do this,
        and only once. Returns (ok, message). Refused attempts are logged.
        """
        when = when or now_text()
        tx_id = parse_request_label(tx_ref)
        customer_id = (customer_id or "").strip()
        choice = "APPROVE" if approve else "REJECT"
        tx = self.get_transaction(tx_id) if tx_id else None

        def refuse(message):
            self._log(when, "APPROVAL_REFUSED", customer_id or None,
                      tx["agent_name"] if tx else None, tx["action"] if tx else None,
                      tx["amount"] if tx else None,
                      request_id=request_label(tx_id) if tx else str(tx_ref),
                      agent_id=tx["agent_id"] if tx else None,
                      status=tx["status"] if tx else None,
                      customer_decision=choice, reason=message)
            self.conn.commit()
            return False, message

        if tx is None:
            return refuse(f"No transaction called '{tx_ref}'.")
        label = request_label(tx_id)
        if customer_id.lower() != (tx["customer"] or "").lower():
            return refuse(f"{label} belongs to another customer. Only its owner can decide.")
        customer = self.get_customer(customer_id)
        if customer is None or not customer["pin_hash"]:
            return refuse(f"Customer {customer_id} has no approval PIN, so {label} cannot be decided.")
        if _hash_pin(pin or "", customer["pin_salt"]) != customer["pin_hash"]:
            return refuse(f"Wrong PIN for {customer_id}. {label} was not changed.")
        if tx["status"] != gk.PENDING:
            return refuse(f"{label} is already {tx['status']} "
                          f"(at {tx['decided_at'] or tx['created_at']}). It cannot be decided twice.")

        new_status, decided_by, rule, reason = (
            gk.APPROVED if approve else gk.REJECTED, f"customer {tx['customer']}",
            tx["rule"], tx["reason"])
        if approve:
            # Safety checks again at the moment of approval
            if self.agent_status(tx["customer"], tx["agent_name"]) != "active":
                new_status, reason = gk.REJECTED, "Agent is no longer active, so it cannot be approved."
                decided_by = "system"
            else:
                spent = self.spent_today(tx["customer"], tx["agent_name"], when[:10])
                if spent + tx["amount"] > gk.DAILY_CAP:
                    new_status, rule = gk.BLOCKED, 6
                    reason = (f"Approval would take today's spending to "
                              f"${spent + tx['amount']:,.2f}, above the "
                              f"${gk.DAILY_CAP:,.2f} daily cap.")

        # Atomic guard: only a row that is still PENDING can change.
        cur = self.conn.execute(
            """UPDATE transactions SET status = ?, rule = ?, reason = ?, decided_at = ?,
                   decided_by = ? WHERE id = ? AND status = ?""",
            (new_status, rule, reason, when, decided_by, tx_id, gk.PENDING))
        if cur.rowcount != 1:
            self.conn.rollback()
            return refuse(f"{label} is no longer pending.")
        self._log(when, "CUSTOMER_DECISION", tx["customer"], tx["agent_name"], tx["action"],
                  tx["amount"], tx["decision"], rule, reason, request_id=label,
                  agent_id=tx["agent_id"], status=new_status, customer_decision=choice,
                  decided_at=when)
        self.conn.commit()
        if new_status == gk.APPROVED:
            return True, f"{label} APPROVED by {tx['customer']} at {when}."
        if new_status == gk.REJECTED and approve:
            return False, f"{label} REJECTED: {reason}"
        if new_status == gk.BLOCKED:
            return False, f"{label} BLOCKED at approval: {reason}"
        return True, f"{label} REJECTED by {tx['customer']} at {when}."

    # ---------- agents ----------

    def register_agent(self, customer, agent_name, permissions=None, when=None):
        """Register an agent for a customer. Returns (ok, message)."""
        when = when or now_text()
        customer = (customer or "").strip()
        agent_name = (agent_name or "").strip()
        if not customer or not agent_name:
            return False, "Enter both a customer ID and an agent name."
        if len(customer) > 60 or len(agent_name) > 60:
            return False, "Customer ID and agent name must be 60 characters or fewer."
        if self.get_customer(customer) is None:
            return False, f"Unknown customer '{customer}'. Agents can only be registered for bank customers."
        perms = gk.ALL_ACTIONS if permissions is None else set(permissions) & gk.ALL_ACTIONS
        if not perms:
            return False, "Give the agent at least one permission."

        row = self._find_agent(customer, agent_name)
        if row is not None and row["revoked_at"]:
            return False, (f"'{agent_name}' was revoked for {customer} on "
                           f"{row['revoked_at']}. A revoked agent stays blocked; "
                           f"register it under a new name if the customer trusts it again.")
        if row is not None:
            return False, (f"'{agent_name}' is already registered for {customer} "
                           f"(since {row['registered_at']}).")

        perm_text = ",".join(sorted(perms))
        cur = self.conn.execute(
            "INSERT INTO agents (customer, agent_name, registered_at, permissions) VALUES (?, ?, ?, ?)",
            (customer, agent_name, when, perm_text))
        self._log(when, "REGISTER", customer, agent_name, agent_id=cur.lastrowid,
                  reason=f"Agent registered at {when} with permissions: {perm_text}.")
        self.conn.commit()
        return True, f"Registered '{agent_name}' for {customer} at {when} ({perm_text})."

    def update_permissions(self, customer, agent_name, permissions, when=None):
        """Change what an active agent is allowed to do. Returns (ok, message)."""
        when = when or now_text()
        customer = (customer or "").strip()
        agent_name = (agent_name or "").strip()
        row = self._find_agent(customer, agent_name)
        if row is None:
            return False, f"No agent called '{agent_name}' is registered for {customer}."
        if row["revoked_at"]:
            return False, f"'{agent_name}' was revoked on {row['revoked_at']}; its permissions cannot change."
        perms = set(permissions or []) & gk.ALL_ACTIONS
        if not perms:
            return False, "Give the agent at least one permission (or revoke it instead)."
        perm_text = ",".join(sorted(perms))
        self.conn.execute("UPDATE agents SET permissions = ? WHERE id = ?", (perm_text, row["id"]))
        self._log(when, "PERMISSIONS", customer, agent_name, agent_id=row["id"],
                  reason=f"Permissions changed from {row['permissions']} to {perm_text}.")
        self.conn.commit()
        return True, f"Updated '{agent_name}' for {customer}: {perm_text}."

    def revoke_agent(self, customer, agent_name, when=None):
        """
        Revoke an agent and save the date and time as proof.
        Any of its PENDING transactions are rejected so they can never be approved.
        Returns (ok, message).
        """
        when = when or now_text()
        customer = (customer or "").strip()
        agent_name = (agent_name or "").strip()

        row = self._find_agent(customer, agent_name)
        if row is None:
            return False, f"No agent called '{agent_name}' is registered for {customer}."
        if row["revoked_at"]:
            return False, f"'{agent_name}' was already revoked on {row['revoked_at']}."

        self.conn.execute("UPDATE agents SET revoked_at = ? WHERE id = ?", (when, row["id"]))
        self._log(when, "REVOKE", customer, agent_name, agent_id=row["id"],
                  reason=f"Access revoked at {when}. This entry is the proof of revocation.")
        pending = self.conn.execute(
            "SELECT * FROM transactions WHERE agent_id = ? AND status = ?",
            (row["id"], gk.PENDING)).fetchall()
        for tx in pending:
            reason = "Agent was revoked before the customer decided."
            self.conn.execute(
                """UPDATE transactions SET status = ?, reason = ?, decided_at = ?,
                       decided_by = 'system' WHERE id = ? AND status = ?""",
                (gk.REJECTED, reason, when, tx["id"], gk.PENDING))
            self._log(when, "AUTO_REJECTED", customer, agent_name, tx["action"], tx["amount"],
                      tx["decision"], tx["rule"], reason, request_id=request_label(tx["id"]),
                      agent_id=row["id"], status=gk.REJECTED, decided_at=when)
        self.conn.commit()
        extra = f" {len(pending)} pending transaction(s) were rejected." if pending else ""
        return True, (f"Revoked '{agent_name}' for {customer} at {when}. "
                      f"The date and time are saved as proof.{extra}")

    # ---------- reading data for the screen ----------

    def list_customers(self):
        return self.conn.execute("SELECT * FROM customers ORDER BY customer_id").fetchall()

    def list_agents(self):
        return self.conn.execute("SELECT * FROM agents ORDER BY id DESC").fetchall()

    def pending_transactions(self):
        return self.conn.execute("SELECT * FROM transactions WHERE status = ? ORDER BY id",
                                 (gk.PENDING,)).fetchall()

    def transactions(self, limit=200):
        return self.conn.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT ?",
                                 (limit,)).fetchall()

    def audit_rows(self, limit=200):
        return self.conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def stats(self, day):
        counts = {s: 0 for s in (gk.ALLOWED, gk.BLOCKED, gk.PENDING, gk.APPROVED, gk.REJECTED)}
        for r in self.conn.execute(
                """SELECT status, COUNT(*) AS n FROM transactions
                   WHERE created_at LIKE ? OR decided_at LIKE ? OR status = ?
                   GROUP BY status""", (day + "%", day + "%", gk.PENDING)):
            counts[r["status"]] = r["n"]
        money = self.conn.execute(
            """SELECT COALESCE(SUM(amount), 0) AS total FROM transactions
               WHERE action IN ('pay_bill', 'transfer_money')
                 AND ((status = ? AND created_at LIKE ?) OR (status = ? AND decided_at LIKE ?))""",
            (gk.ALLOWED, day + "%", gk.APPROVED, day + "%")).fetchone()["total"]
        agents = self.conn.execute(
            """SELECT SUM(revoked_at IS NULL) AS active, SUM(revoked_at IS NOT NULL) AS revoked
               FROM agents""").fetchone()
        return {"counts": counts, "completed_money": float(money),
                "active_agents": agents["active"] or 0, "revoked_agents": agents["revoked"] or 0}

    # ---------- CSV exports ----------

    def export_csv(self):
        """Full audit log as CSV (oldest first)."""
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(AUDIT_COLUMNS)
        for row in self.conn.execute("SELECT * FROM audit_log ORDER BY id"):
            writer.writerow([row[c] for c in AUDIT_COLUMNS])
        return out.getvalue()

    export_audit_csv = export_csv

    def export_transactions_csv(self):
        """Every transaction with its CURRENT status (oldest first)."""
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(TRANSACTION_COLUMNS)
        for row in self.conn.execute("SELECT * FROM transactions ORDER BY id"):
            values = dict(row)
            values["request_id"] = request_label(row["id"])
            writer.writerow([values.get(c) for c in TRANSACTION_COLUMNS])
        return out.getvalue()

    # ---------- demo helpers ----------

    def load_demo_data(self):
        """Sample agents so the test cases can be run straight away."""
        self.register_agent("C1001", "BudgetBot")
        self.register_agent("C1001", "ShopperGPT")
        self.revoke_agent("C1001", "ShopperGPT")
        self.register_agent("C1002", "FinanceBuddy", permissions={"view_balance"})

    def reset(self, confirm_text="RESET"):
        """Delete agents, transactions and the audit log (customers stay).
        Only runs when confirm_text is exactly 'RESET', so it cannot happen by accident."""
        if confirm_text != "RESET":
            return False, "Nothing was deleted. Type RESET (in capitals) to confirm."
        for table in ("agents", "transactions", "audit_log"):
            self.conn.execute(f"DELETE FROM {table}")
        # Restart numbering so the demo starts again at TX-0001 / AG-001.
        self.conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('agents', 'transactions', 'audit_log')")
        self.conn.commit()
        return True, "All agents, transactions and the audit log were deleted. Demo customers were kept."

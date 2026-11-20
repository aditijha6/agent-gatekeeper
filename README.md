# Agent Gatekeeper: JPMorgan Chase (academic prototype)

**Enrolment number:** PGD202571184 · **Category:** Bank · **Company:** JPMorgan Chase

> Academic prototype only. It is not an official JPMorgan Chase product and is not connected to any real banking system. All customers, agents and money in it are made up.

## 1. Objective

Build a small working "gatekeeper" that sits between a bank customer's AI agent and the bank. For each request it decides whether to **ALLOW** it, **ASK THE CUSTOMER**, or **BLOCK** it, gives the reason and rule number, keeps an audit log, and lets the customer register and revoke agents.

## 2. Problem statement

Customers now use personal AI agents to check balances, pay bills and move money. Banks must decide what these agents may do. JPMorgan Chase currently blocks outside agents from acting for retail customers, while allowing read-only data through connectors such as Plaid. Wells Fargo now asks customers to keep proof that they revoked an agent. The question for a bank is: **when an agent asks for something, should the bank allow it, ask the customer, or block it, and how does it record and cancel the agent's permission?** See [RULES.md](RULES.md) for sources.

## 3. How it works

```
AI agent request ──► gatekeeper.decide() ──► ALLOW         → transaction ALLOWED
 (customer, agent,     rules 1-8, first        ASK CUSTOMER  → transaction PENDING ──► customer approves → APPROVED
  action, amount)      match wins              BLOCK         → transaction BLOCKED  └─► customer rejects → REJECTED
                                   every step is written to the audit log
```

1. An agent's request (customer ID, agent name, action, amount) is entered in the **Transaction simulator**.
2. `storage.py` looks up the customer and the agent (unknown, active or revoked, and its permissions) and how much the agent has already **completed** today.
3. `gatekeeper.decide()` checks rules 1–8 in order and stops at the first match.
4. The request is saved as a **transaction** with status ALLOWED, BLOCKED or PENDING, and as a row in the **audit log**.
5. PENDING transactions wait under **Pending customer approvals** until the customer approves or rejects them with their PIN.

### Security rules (summary; full details in RULES.md)

| # | Rule | Decision |
|---|------|----------|
| 1 | Unknown agent or unknown customer | BLOCK |
| 2 | Revoked agent | BLOCK |
| 3 | Unsupported action, or action not permitted for this agent | BLOCK |
| 4 | View balance (read-only) | ALLOW |
| 5 | Missing, zero, negative or non-numeric amount | BLOCK |
| 6 | Would take the agent's completed spending today above $2,000 | BLOCK |
| 7 | Any transfer, or a bill above $500 | ASK CUSTOMER → PENDING |
| 8 | Bill of $500 or less | ALLOW |

The $500 and $2,000 limits are **demonstration values** set in `config.py`, not JPMorgan Chase policy.

### Customer approval workflow

- A PENDING transaction never moves money and never counts as completed.
- Only the customer who owns it, with the correct PIN, can **Approve** (status becomes APPROVED) or **Reject** (status becomes REJECTED). Another customer, a wrong PIN or an agent is refused, and the attempt is logged.
- Each transaction can be decided only once.
- At approval time the agent must still be active and the daily cap is checked again.
- Revoking an agent rejects its pending transactions automatically.
- Demo customers: **C1001 (PIN 1111)**, **C1002 (PIN 2222)**, **C1003 (PIN 3333)**. PINs are stored hashed, never as plain text.

## 4. Technology used

- **Python 3.8 or newer**, standard library only, with **nothing to install**:
  - `http.server` for the local website
  - `sqlite3` for the database
  - `unittest` for the tests
  - `hashlib` for hashing the PINs
- Plain HTML and CSS produced by `app.py`, with no JavaScript framework.

## 5. Database (`gatekeeper.db`, created automatically)

| Table | What it stores |
|-------|----------------|
| `customers` | Demo customers and a salted hash of each approval PIN |
| `agents` | Agent ID, customer, name, permissions, `registered_at`, `revoked_at` (revocation proof) |
| `transactions` | Request ID (TX-0001…), date and time, customer, agent, action, amount, rule, decision, **status** (ALLOWED / BLOCKED / PENDING / APPROVED / REJECTED), who decided and when |
| `audit_log` | Append-only history: `REQUEST`, `CUSTOMER_DECISION`, `APPROVAL_REFUSED`, `AUTO_REJECTED`, `REGISTER`, `PERMISSIONS`, `REVOKE`. Rows are never edited. |

**Upgrading:** an older `gatekeeper.db` from the first version is upgraded automatically when the app starts. New tables and columns are added, nothing is deleted, and old agents keep all three permissions. A test checks this (`test_old_database_is_upgraded_safely`).

**Deleting data:** only the **Reset** tool deletes data, and only after you type `RESET`. Demo customers are kept.

## 6. Files

| File | What it does |
|------|--------------|
| `gatekeeper.py` | **The rules.** `decide()` returns the decision, rule number and reason. |
| `storage.py` | Database: customers, agents, transactions, approval workflow, audit log, CSV export. |
| `app.py` | The dashboard website. |
| `config.py` | Enrolment number, company name and the two demonstration limits. |
| `run_app.bat` / `run_tests.bat` | Double-click launchers for Windows. |
| `tests/test_gatekeeper.py` | The original 14 tests (unchanged). |
| `tests/test_workflow.py` | 25 tests for approvals, permissions, audit, CSV, database upgrade, and an end-to-end website test. |
| `RULES.md`, `TEST_CASES.md`, `PROMPTS.md`, `VIDEO_SCRIPT.md` | Rules and sources, test plan and results, AI prompts and personal checks, demo script. |

## 7. How to run it on Windows

**Before you start:** you need Python. In Command Prompt type `py --version`. If you see `Python 3.x.x`, you're ready. If not, install Python from https://www.python.org/downloads/ and tick **"Add python.exe to PATH"** on the first installer screen.

### Easiest way: double-click
1. Unzip the project and open the `agent-gatekeeper` folder.
2. Double-click **`run_tests.bat`** to run all tests. The window should end with `OK`. The results are also saved in `test_output.txt`.
3. Double-click **`run_app.bat`** to start the app. Your browser opens at **http://127.0.0.1:8000**.
4. **To stop the app,** close the black window, or click it and press **Ctrl + C**.

If Windows shows "Windows protected your PC", click **More info**, then **Run anyway**.

### With Command Prompt
1. Open the `agent-gatekeeper` folder in File Explorer, click the address bar, type `cmd` and press **Enter**. A Command Prompt opens in that folder.
2. Run the tests: `py -m unittest -v`
3. Start the app: `py app.py`. If `py` doesn't work, use `python` instead.
4. Open **http://127.0.0.1:8000**. If port 8000 is busy, the window prints the address it used instead, such as 8001.
5. To stop it, press **Ctrl + C** in that window.

### With VS Code
1. **File → Open Folder…** and choose `agent-gatekeeper`.
2. **Terminal → New Terminal**.
3. Type the same commands: `py -m unittest -v`, then `py app.py`.

## 8. Testing

- **Method:** automated unit tests for every rule, the approval workflow, the audit log, the CSV export and the database upgrade, plus one end-to-end test that starts the real web server and approves and rejects over HTTP. The six manual test cases in `TEST_CASES.md` are for running by hand in the browser.
- **Actual results (run by Claude on 20 Nov 2026, Linux, Python 3.11, 3.12 and 3.13):** **39 tests, 39 passed, 0 failed** on each version. These results are not from your Windows laptop; record your own run in TEST_CASES.md.

## 9. Demonstration sequence (presentation)

See [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md) for the full script. In short:
1. Show the header with the enrolment number and the "academic prototype" note.
2. Type `RESET` and click Reset, then click **Load demo agents**.
3. Run TC1–TC4: an unknown agent is BLOCKED, a revoked agent is BLOCKED, viewing the balance is ALLOWED, a $120 bill is ALLOWED.
4. Run TC5: a $750 bill becomes PENDING. Approve it with C1001 / 1111, and the status becomes APPROVED.
5. Run TC6: a $50 transfer becomes PENDING. Try PIN 9999 (refused), then Reject it with 1111. The status becomes REJECTED.
6. Try approving the same transaction again. It is refused.
7. Ask FinanceBuddy (C1002) to pay a bill. It is BLOCKED by rule 3, because it doesn't have that permission.
8. Revoke BudgetBot. Its time is saved, its pending items are rejected, and its next request is BLOCKED by rule 2.
9. Show the Transaction history, the Audit log and both CSV downloads.

## 10. Limitations

- This is a local demo. There is no real login, no real bank connection and no real money.
- Customer PINs are a simple stand-in for real customer authentication, such as app sign-in or two-factor.
- The agent is identified only by its name. A real bank would verify agents cryptographically, for example with tokens or OAuth.
- The daily cap uses the computer's local date.
- The app is tested automatically on Linux. You still need to check it on your own Windows laptop.

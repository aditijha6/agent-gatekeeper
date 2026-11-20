# Test Cases: Agent Gatekeeper (JPMorgan Chase academic prototype)

There are two kinds of testing:
- **Part A, manual:** you click through the website and record what you see. This is your own evidence.
- **Part B, automated:** `py -m unittest -v` (or double-click `run_tests.bat`) runs 39 tests.

---

## Part A: Manual test cases (do these yourself in the browser)

**Setup:** start the app (`run_app.bat`). Under **Rules & tools**, type `RESET` and click **Delete agents, transactions and log**, then click **Load demo agents**. This creates:
- C1001 / BudgetBot: active, all permissions
- C1001 / ShopperGPT: revoked
- C1002 / FinanceBuddy: active, View balance only

Demo PINs: C1001 = 1111, C1002 = 2222. Requests go in the **Transaction simulator**, and approvals in **Pending customer approvals**. Leave Amount empty where it says "(empty)".

| # | What it tests | What to do | Expected result | Your actual result | Pass? |
|---|---------------|------------|-----------------|--------------------|-------|
| TC1 | Unknown agent | C1001, RogueBot, View balance, (empty) | BLOCKED · Rule 1 (TX-0001) | | |
| TC2 | Revoked agent, even read-only | C1001, ShopperGPT, View balance, (empty) | BLOCKED · Rule 2 | | |
| TC3 | Balance enquiry allowed | C1001, BudgetBot, View balance, (empty) | ALLOWED · Rule 4 | | |
| TC4 | Small bill allowed | C1001, BudgetBot, Pay a bill, 120 | ALLOWED · Rule 8 | | |
| TC5 | Big bill needs the customer | C1001, BudgetBot, Pay a bill, 750 | PENDING · Rule 7 (TX-0005), listed under Pending approvals | | |
| TC5a | Customer approves | On TX-0005, enter C1001 and PIN 1111, click **Approve** | "TX-0005 APPROVED by C1001"; status APPROVED in Transaction history | | |
| TC6 | Transfer needs the customer | C1001, BudgetBot, Transfer money, 50 | PENDING · Rule 7 (TX-0006) | | |
| TC6a | Wrong PIN refused | On TX-0006, enter C1001 and PIN 9999, click Approve | "Wrong PIN… TX-0006 was not changed"; still PENDING | | |
| TC6b | Customer rejects | On TX-0006, enter C1001 and PIN 1111, click **Reject** | "TX-0006 REJECTED by C1001"; status REJECTED | | |

**Extra checks for the demo:**

| # | What to do | Expected result | Your actual result |
|---|------------|-----------------|--------------------|
| X1 | Look at the **Money completed today** tile in the Dashboard overview | $870.00 = $120 (TC4) + $750 (TC5a); the rejected $50 is not counted | |
| X2 | C1002, FinanceBuddy, Pay a bill, 20 | BLOCKED · Rule 3: no permission to pay a bill | |
| X3 | Revoke C1001 / BudgetBot, then request C1001, BudgetBot, View balance | Agents table shows REVOKED with the date and time; the request is BLOCKED · Rule 2 | |
| X4 | Click **Download transactions (CSV)** and **Download audit log (CSV)** | The CSVs show ALLOWED, BLOCKED, APPROVED, REJECTED and the CUSTOMER_DECISION rows | |

**Evidence to keep:** a screenshot after TC1–TC6b (with the coloured message bar visible), one of the Transaction history and one of the Audit log, plus the two CSV files. Press **Windows key + Print Screen**; the pictures are saved in *Pictures → Screenshots*.

### Run by Claude (AI tool) in its own workspace, 20 Nov 2026, not on your laptop

The same steps were sent to the running website. The messages shown were:

| # | Claude's actual result |
|---|------------------------|
| TC1 | BLOCKED (BLOCK) · Rule 1 · Agent is not registered for this customer. (TX-0001) |
| TC2 | BLOCKED (BLOCK) · Rule 2 · Agent's access has been revoked. (TX-0002) |
| TC3 | ALLOWED (ALLOW) · Rule 4 · Read-only action: no money moves. (TX-0003) |
| TC4 | ALLOWED (ALLOW) · Rule 8 · Bill of $120.00 is within the $500.00 limit. (TX-0004) |
| TC5 | PENDING (ASK CUSTOMER) · Rule 7 · Bill of $750.00 is above the $500.00 limit. (TX-0005) |
| TC5a | TX-0005 APPROVED by C1001 |
| TC6 | PENDING (ASK CUSTOMER) · Rule 7 · Transfers always need the customer's confirmation. (TX-0006) |
| TC6a | Wrong PIN for C1001. TX-0006 was not changed. |
| TC6b | TX-0006 REJECTED by C1001 |
| Approve TX-0005 again | TX-0005 is already APPROVED … It cannot be decided twice. |
| X2 | BLOCKED (BLOCK) · Rule 3 · Agent does not have permission to pay a bill. (TX-0007) |
| X3 | Revoked 'BudgetBot' … The date and time are saved as proof. Then BLOCKED · Rule 2 (TX-0008) |
| X4 | transactions.csv: TX-0001 BLOCKED, TX-0002 BLOCKED, TX-0003 ALLOWED, TX-0004 ALLOWED, TX-0005 APPROVED, TX-0006 REJECTED, TX-0007 BLOCKED, TX-0008 BLOCKED |

---

## Part B: Automated tests

**How to run:** double-click `run_tests.bat`, or in Command Prompt in the project folder type `py -m unittest -v`.

### The 16 required checks and the test that covers each

| # | Required check | Test name (in `tests/test_workflow.py` unless noted) |
|---|----------------|-------------------------------------|
| 1 | Unknown agent is blocked | `test_W01_unknown_agent_blocked`, `test_W01b_unknown_customer_blocked`, TC1 (original) |
| 2 | Revoked agent is blocked | `test_W02_revoked_agent_blocked`, TC2 (original) |
| 3 | Authorised balance enquiry is allowed | `test_W03_authorized_balance_enquiry_allowed`, TC3 (original) |
| 4 | Small permitted transaction is allowed | `test_W04_small_permitted_payment_allowed`, TC4 (original) |
| 5 | Consent needed → pending | `test_W05_consent_needed_becomes_pending` |
| 6 | Approval → APPROVED | `test_W06_customer_approval_sets_approved` |
| 7 | Rejection → REJECTED | `test_W07_customer_rejection_sets_rejected` |
| 8 | Pending not counted as completed | `test_W08_pending_not_counted_as_completed` |
| 9 | Rejected not counted as completed | `test_W09_rejected_not_counted_as_completed` |
| 10 | Duplicate approval prevented | `test_W10_duplicate_approval_prevented` |
| 11 | Unauthorised approval prevented | `test_W11_unauthorized_approval_prevented` (wrong PIN, other customer, no PIN, agent "approve" action), `test_W11b_revoking_agent_rejects_its_pending_transactions` |
| 12 | Invalid amounts blocked | `test_W12_invalid_amounts_blocked`, `test_bad_amounts_are_blocked` (original) |
| 13 | Daily cap enforced | `test_W13_daily_cap_enforced_on_request_and_on_approval`, `test_daily_cap_blocks_after_2000` (original) |
| 14 | Unsupported actions blocked | `test_W14_unsupported_action_blocked`, `test_unsupported_action_is_blocked` (original) |
| 15 | Audit records reflect decisions | `test_W15_audit_log_reflects_decisions`, `test_every_request_is_logged` (original) |
| 16 | CSV export has the correct statuses | `test_W16_csv_exports_show_real_statuses` |

**Also tested:** the permission block (`W03b`), updating permissions, registering an agent for an unknown customer, Reset needing `RESET`, PINs not stored as plain text, upgrading an old database without losing data, and an **end-to-end website test** that starts the real server and approves and rejects over HTTP.

The **original 14 tests** in `tests/test_gatekeeper.py` were kept unchanged.

### Actual automated results

| Run | Where | Result |
|-----|-------|--------|
| Claude, 20 Nov 2026 | Claude's Linux workspace, Python 3.11, 3.12 and 3.13 | **39 run, 39 passed, 0 failed** on each version |
| Claude, 20 Nov 2026 | Same workspace, with the PIN check, the double-approval guard or the "completed money" rule broken on purpose | The tests **failed** each time, showing they really detect those bugs |
| **You** | Your Windows laptop (`run_tests.bat`) | Fill in: ___ run, ___ passed, ___ failed. Python version: ______ |

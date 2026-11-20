# Test Cases: Agent Gatekeeper (JPMorgan Chase)

**Setup before testing:** run `python app.py`, click **Reset all data**, then click **Load demo agents**. This creates:
- C1001 / BudgetBot: active
- C1001 / ShopperGPT: revoked
- C1002 / FinanceBuddy: active

Run each test in box **1. Agent request**. Leave the Amount empty where it says "(empty)". Fill in the **Actual result** column with what the screen really shows.

| # | What it tests | Customer | Agent | Action | Amount | Expected | Actual result (fill in) | Pass? |
|---|---------------|----------|-------|--------|--------|----------|-------------------------|-------|
| TC1 | Unknown agent | C1001 | RogueBot | View balance | (empty) | BLOCK, Rule 1 | | |
| TC2 | Revoked agent, even read-only | C1001 | ShopperGPT | View balance | (empty) | BLOCK, Rule 2 | | |
| TC3 | Read-only allowed | C1001 | BudgetBot | View balance | (empty) | ALLOW, Rule 4 | | |
| TC4 | Small bill allowed | C1001 | BudgetBot | Pay a bill | 120 | ALLOW, Rule 8 | | |
| TC5 | Bill above $500 | C1001 | BudgetBot | Pay a bill | 750 | ASK CUSTOMER, Rule 7 | | |
| TC6 | Transfer always asks | C1001 | BudgetBot | Transfer money | 50 | ASK CUSTOMER, Rule 7 | | |

**Revocation check (the Wells Fargo problem):**
1. In box 3, revoke **C1002 / FinanceBuddy**.
2. Check that the Registered agents table shows REVOKED with a date and time.
3. Send a View balance request for C1002 / FinanceBuddy. Expected: BLOCK, Rule 2.

## Run 1: by Claude (AI tool), in its own workspace, 20 Nov 2026

Run through the live web app (same inputs as above), and again with `python -m unittest -k TC`. Times in its log are UTC (12:36 UTC = 18:06 IST).

| # | Expected | Claude's actual result | Pass? |
|---|----------|------------------------|-------|
| TC1 | BLOCK, Rule 1 | BLOCK · Rule 1 · Agent is not registered for this customer. | ✅ |
| TC2 | BLOCK, Rule 2 | BLOCK · Rule 2 · Agent's access has been revoked. | ✅ |
| TC3 | ALLOW, Rule 4 | ALLOW · Rule 4 · Read-only action: no money moves. | ✅ |
| TC4 | ALLOW, Rule 8 | ALLOW · Rule 8 · Bill of $120.00 is within the $500.00 limit. | ✅ |
| TC5 | ASK CUSTOMER, Rule 7 | ASK CUSTOMER · Rule 7 · Bill of $750.00 is above the $500.00 limit. | ✅ |
| TC6 | ASK CUSTOMER, Rule 7 | ASK CUSTOMER · Rule 7 · Transfers always need the customer's confirmation. | ✅ |
| Revocation | BLOCK, Rule 2 | Revoked C1002 / FinanceBuddy with the time saved, then BLOCK · Rule 2 | ✅ |

Automated: 6/6 TC tests OK (14/14 including the extra checks).

## Run 2: by me, on my own computer

Fill in the "Actual result" column in the first table above.

**Evidence to keep:** a screenshot after each test showing the coloured result bar, a screenshot of the audit log table at the end, and the downloaded `audit_log.csv`.

**Automated version:** `python -m unittest -v` runs TC1–TC6 plus eight extra checks (rules 3, 5 and 6, revocation proof, and more). Results recorded by the developer environment on 20 Nov 2026: 14 tests, all passed. Re-run this on your own computer and record your result.

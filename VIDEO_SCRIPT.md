# Demo video and presentation script (about 5 minutes)

Record your screen in your own voice. On Windows, press **Win + Alt + R** to start and stop recording with the Xbox Game Bar. Say things in your own words; the lines below are a guide, not something to read word for word.

**Before you press record:** double-click `run_app.bat`. Under **Rules & tools**, type `RESET` and click Delete, then click **Load demo agents**. Scroll to the top.

| Time | Show on screen | What to do and say |
|------|----------------|--------------------|
| 0:00–0:30 | Header and Dashboard overview | "This is my Agent Gatekeeper, an academic prototype based on JPMorgan Chase. My enrolment number is PGD202571184. It ends in 4, so my category is a bank. Customers now use AI agents, and the bank must decide: allow, ask the customer, or block." |
| 0:30–1:00 | Security rules card | "There are 8 rules, checked in order, and the first match wins. JPMorgan currently blocks outside agents but allows read-only balance access, so viewing the balance is allowed and money is controlled. My $500 and $2,000 limits are demo values I chose, not JPMorgan policy." |
| 1:00–1:45 | Simulator: TC1 to TC4 | RogueBot → BLOCKED, Rule 1. ShopperGPT → BLOCKED, Rule 2 (revoked). BudgetBot views the balance → ALLOWED, Rule 4. BudgetBot pays a $120 bill → ALLOWED, Rule 8. Point at the coloured bar and rule number each time. |
| 1:45–2:45 | TC5 and the approval box | BudgetBot pays a $750 bill → **PENDING**. "No money moves yet. Only the customer can decide." Enter C1001 and PIN 1111, then click **Approve** → APPROVED. |
| 2:45–3:30 | TC6 | BudgetBot transfers $50 → PENDING. Enter PIN 9999 → refused. "A wrong PIN, another customer, or the agent itself can't approve." Then PIN 1111 and **Reject** → REJECTED. |
| 3:30–3:50 | Overview tiles | "Money completed today is $870: the $120 and the $750. The rejected transfer isn't counted, and neither are pending ones." |
| 3:50–4:20 | Permissions and revocation | FinanceBuddy (C1002) pays a $20 bill → BLOCKED, Rule 3, because it may only view the balance. Revoke BudgetBot → the agents table shows REVOKED with the time. "This is the Wells Fargo problem: proof of revocation." BudgetBot views the balance → BLOCKED, Rule 2. |
| 4:20–4:45 | Transaction history and Audit log | "Every request has an ID and a status, and the audit log keeps every event, including refused approvals. Nothing is edited." Click both CSV downloads. |
| 4:45–5:00 | `gatekeeper.py`, the `decide()` function | "All the rules are in this one function, one if-check per rule. The approval workflow is in `storage.py`, in `customer_decision()`." Mention any change you made yourself. |

## Questions your professor might ask (practise answering in your own words)

- **Why is viewing the balance allowed but transfers aren't?** It's read-only and can't lose money. JPMorgan reportedly allows read-only access through Plaid.
- **What stops an agent from approving its own payment?** Approval needs the customer's own ID and PIN, and there is no "approve" action for agents. If one tries, rule 3 blocks it.
- **What happens if you click Approve twice?** The second time is refused, because only a PENDING transaction can change.
- **Why does rule order matter?** A revoked agent asking only to view the balance must hit rule 2 before rule 4 could allow it.
- **Where are the limits set?** In `config.py`. They are demo values, not JPMorgan's.
- **How do you prove an agent was revoked?** `revoked_at` is saved in the agents table, and a REVOKE row is added to the audit log, which is never edited.

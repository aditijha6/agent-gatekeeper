# Demo video plan and script (about 4 minutes)

Record your screen with your own voice. Free options: the Xbox Game Bar on Windows (Win + Alt + R) or QuickTime on a Mac. Speak in your own words; the lines below are a guide, not something to read word for word.

**Before you press record:** start the app, click **Reset all data**, then **Load demo agents**.

| Time | Show on screen | What to say |
|------|----------------|-------------|
| 0:00–0:30 | The page header with your enrolment number | "This is my Agent Gatekeeper for JPMorgan Chase. My enrolment number is PGD202571184. It ends in 4, so I picked a bank. Customers now use AI agents to act for them, and the bank has to decide: allow, ask the customer, or block." |
| 0:30–1:00 | The rules card | "These are my 8 rules. They're checked in order, and the first one that matches wins. JPMorgan currently blocks outside agents but lets balances through, so read-only access is allowed and money actions are controlled. My limit is $500, a quarter of Chase's typical $2,000 daily Zelle limit." |
| 1:00–2:30 | Run TC1 to TC6 one by one | Say what you expect before clicking, then point at the result bar and rule number. |
| 2:30–3:15 | Revoke C1002 / FinanceBuddy, show the agents table, then send a request from it | "This is the Wells Fargo problem: customers must prove they revoked an agent. The revocation time is saved here and in the audit log, and the agent is now blocked by rule 2." |
| 3:15–3:45 | Scroll to the audit log, then click Download CSV | "Every request is logged with the date and time, the decision and the rule." |
| 3:45–4:00 | `gatekeeper.py`, the `decide` function | "All the logic is in this one function: an if-check per rule, in order." Mention your own code change here. |

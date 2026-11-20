# Agent Gatekeeper Rules: JPMorgan Chase (academic prototype)

**Enrolment number:** PGD202571184 (last digit 4 → bank)
**Company:** JPMorgan Chase (retail banking)
**Actions:** view balance, pay a bill, transfer money
**Decisions:** ALLOW, ASK CUSTOMER, BLOCK

> This is an academic prototype. It is **not** an official JPMorgan Chase product, it is not connected to any JPMorgan Chase system, and its rules are **not** JPMorgan Chase policy. It shows how a bank *could* control AI agents that try to use banking functions.

The rules are checked in order. The **first rule that matches** decides the outcome.

| # | Rule | Decision |
|---|------|----------|
| 1 | **Unknown agent:** the agent is not registered for this customer, or the customer is not a known bank customer. | BLOCK |
| 2 | **Revoked agent:** the agent's access was revoked. The revocation date and time are saved as proof, and a revoked agent is always blocked. | BLOCK |
| 3 | **Unsupported or not permitted action:** anything other than view balance, pay a bill or transfer money, or an action the customer did not give this agent permission for. | BLOCK |
| 4 | **Read-only action:** view balance cannot move money. | ALLOW |
| 5 | **Invalid amount:** a money action with a missing, zero, negative or non-numeric amount. | BLOCK |
| 6 | **Daily cap:** the request would take the agent's *completed* spending today above **$2,000**. This is checked again at the moment the customer approves. | BLOCK |
| 7 | **Needs customer confirmation:** every transfer, and any bill above **$500**. The transaction becomes **PENDING** until the customer approves or rejects it. | ASK CUSTOMER |
| 8 | **Small bill:** a bill payment of $500 or less. | ALLOW |

**Why $500 (one line):** it is a quarter of the roughly $2,000 a day that a Chase personal checking customer can send by Zelle, as reported by Wise, so routine bills go through but anything bigger needs the customer's own yes.

**Both limits are demonstration values chosen for this project**, not official JPMorgan Chase limits. They live in `config.py` (`CONFIRM_LIMIT`, `DAILY_CAP`) and can be changed there.

## The customer approval workflow (rule 7)

1. The agent's request is saved as a **PENDING** transaction (for example TX-0004). No money moves.
2. It appears under **Pending customer approvals** with the agent, action, amount and reason.
3. Only the **customer who owns it** can decide, by entering their customer ID and **PIN**. Another customer, a wrong PIN or an agent cannot. Every refused attempt is logged as `APPROVAL_REFUSED`.
4. **Approve** changes the status to **APPROVED**, and **Reject** changes it to **REJECTED**. The decision, who made it and the date and time are saved.
5. A transaction can be decided **only once**. A second approve or reject is refused.
6. When the customer approves, rules 2 and 6 are checked again. If the agent was revoked meanwhile, the transaction is REJECTED. If the approval would break the daily cap, it is BLOCKED.
7. Revoking an agent automatically rejects all of its pending transactions.
8. Only **ALLOWED** and **APPROVED** payments count as completed money. PENDING, REJECTED and BLOCKED never do.

## What is real (with sources) and what is designed for this prototype

| Statement | Type |
|-----------|------|
| JPMorgan Chase blocks outside AI agents from acting on behalf of retail customers or logging in with their credentials; a spokesperson confirmed this to CNBC. | **Reported fact:** PYMNTS, The Paypers, Cybernews |
| Outside agents can still see balances in read-only form when the customer has authorised a connector such as Plaid, but cannot send money or pay bills. | **Reported fact:** PYMNTS, Cybernews |
| CEO Jamie Dimon warned about "rogue agents" on the bank's third-quarter 2026 earnings call. | **Reported fact:** The Paypers, Cybernews |
| Wells Fargo's updated Online Access Agreement (effective 24 Nov 2026) makes customers responsible for revoking an AI agent and keeping proof of revocation. | **Reported fact:** Wells Fargo, American Banker |
| Chase personal checking Zelle limit of about $2,000/day. | **Third-party report** (Wise); Chase says limits are shown per transaction in its app |
| Registering agents, per-agent permissions, customer PINs, the $500 limit, the $2,000 daily cap and the approval workflow. | **Designed for this prototype**, not JPMorgan Chase policy |

## How the rules connect to these facts

- **Rule 4:** read-only access is allowed, mirroring the reported read-only access through connectors like Plaid.
- **Rules 1–3:** only agents the customer registered, did not revoke and gave permission to can act. This addresses the "rogue agents" concern.
- **Rule 2 and the audit log:** these save the revocation date and time, the kind of proof Wells Fargo now asks customers to keep.
- **Rules 6–8:** today JPMorgan does not let outside agents move money at all. This prototype shows a possible middle ground, where small bills are allowed and everything else needs the customer's own approval.

## Sources

- PYMNTS, "Jamie Dimon Slams the Door on Rogue AI Agents": https://www.pymnts.com/?p=4312577
- The Paypers, "JPMorgan Chase blocks external AI agents from customer accounts": https://thepaypers.com/fintech/news/jpmorgan-chase-blocks-external-ai-agents-from-customer-accounts
- Cybernews, "JPMorgan blocks outside AI agents from customer accounts": https://cybernews.com/security/jpmorgan-chase-blocks-outside-ai-agents/
- OfficeChai (Oct 2026), citing TechCrunch: https://officechai.com/ai/amazon-jpmorgan-schwab-and-delta-are-all-blocking-ai-agents-heres-why/
- Wells Fargo, "We Are Updating Our Online Access Agreement": https://www.wellsfargo.com/online-banking/updates/
- American Banker (2 Nov 2026): https://www.americanbanker.com/news/wells-fargo-wants-customers-to-prove-theyve-revoked-ai-agents
- Wise, Zelle transfer limits: https://wise.com/us/blog/zelle-transfer-limits

# Agent Gatekeeper Rules: JPMorgan Chase

**Enrolment number:** PGD202571184 (last digit 4 → bank)
**Company:** JPMorgan Chase (retail banking)
**Actions:** view balance, pay a bill, transfer money
**Decisions:** ALLOW, ASK CUSTOMER, BLOCK

The rules are checked in order. The **first rule that matches** decides the outcome.

| # | Rule | Decision |
|---|------|----------|
| 1 | **Unknown agent:** the agent is not registered for this customer. | BLOCK |
| 2 | **Revoked agent:** the agent's access was revoked. The revocation date and time are saved as proof, and a revoked agent is always blocked. | BLOCK |
| 3 | **Unsupported action:** anything other than view balance, pay a bill or transfer money. | BLOCK |
| 4 | **Read-only action:** view balance cannot move money. | ALLOW |
| 5 | **Invalid amount:** a money action with a missing, zero, negative or non-numeric amount. | BLOCK |
| 6 | **Daily cap:** the request would take the agent's allowed spending today above **$2,000**. | BLOCK |
| 7 | **Needs confirmation:** every transfer, and any bill above **$500**. | ASK CUSTOMER |
| 8 | **Small bill:** a bill payment of $500 or less. | ALLOW |

**Why $500:** it is a quarter of the roughly $2,000 a day that a Chase personal checking customer can send by Zelle, so routine bills go through but anything bigger needs the customer's own yes.

## Why these rules fit JPMorgan Chase

- JPMorgan currently blocks outside AI agents from acting for retail customers, but read-only data such as balances can still reach them through data providers like Plaid. Rule 4 allows read-only access, and rules 6–8 control money.
- Jamie Dimon warned about "rogue agents". Rules 1 and 2 mean only agents the customer has registered, and not revoked, can act.
- Wells Fargo's new agreement (effective 24 Nov 2026) makes customers keep proof that they revoked an agent. Rule 2 saves the revocation date and time in the agents table and in the audit log.
- Money sent to a person is hard to get back, so rule 7 asks the customer before **every** transfer. Bills go to known billers, so small ones are allowed.
- A revoked agent cannot be re-registered under the same name. The customer must register a new agent, so the old revocation record is never overwritten.

## Sources

- OfficeChai (Oct 2026), citing TechCrunch: https://officechai.com/ai/amazon-jpmorgan-schwab-and-delta-are-all-blocking-ai-agents-heres-why/
- American Banker (2 Nov 2026), Wells Fargo revocation proof: https://www.americanbanker.com/news/wells-fargo-wants-customers-to-prove-theyve-revoked-ai-agents
- Chase Zelle limit (~$2,000/day for personal checking, per Wise; Chase says limits are set per transaction): https://wise.com/us/blog/zelle-transfer-limits

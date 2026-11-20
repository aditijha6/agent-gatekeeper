"""
Agent Gatekeeper - the decision rules (JPMorgan Chase prototype).

decide() is the heart of the project. It receives the facts about ONE request
from a customer's AI agent and returns ALLOW, ASK CUSTOMER or BLOCK, together
with the number of the rule that caused the decision and a short reason.

Rules are checked in order from 1 to 8. The FIRST rule that matches wins.
Order matters: e.g. a revoked agent asking only to view the balance must be
blocked by rule 2 before rule 4 could allow it.
"""

import math
from dataclasses import dataclass

# The three possible decisions
ALLOW = "ALLOW"
ASK = "ASK CUSTOMER"
BLOCK = "BLOCK"

# Bank actions the gatekeeper understands
READ_ONLY_ACTIONS = {"view_balance"}
MONEY_ACTIONS = {"pay_bill", "transfer_money"}
ACTION_LABELS = {
    "view_balance": "View balance",
    "pay_bill": "Pay a bill",
    "transfer_money": "Transfer money",
}

# Limits (US dollars)
# $500 = a quarter of the ~$2,000/day Zelle limit for a Chase personal checking
# account: routine bills go through, anything bigger needs the customer's yes.
CONFIRM_LIMIT = 500.00
# An agent may never move more in one day than the customer's own typical
# daily Zelle limit at Chase.
DAILY_CAP = 2000.00

# (rule number, short name, decision, plain-English description)
RULES = [
    (1, "Unknown agent", BLOCK,
     "An agent that is not registered for this customer is blocked."),
    (2, "Revoked agent", BLOCK,
     "An agent whose access was revoked is always blocked. The date and time "
     "of revocation are saved as proof."),
    (3, "Unsupported action", BLOCK,
     "Only view balance, pay a bill and transfer money are recognised. "
     "Anything else is blocked."),
    (4, "Read-only action", ALLOW,
     "Viewing the balance cannot move money, so it is allowed."),
    (5, "Invalid amount", BLOCK,
     "A money action with a missing, zero, negative or non-numeric amount "
     "is blocked."),
    (6, "Daily cap", BLOCK,
     f"If the request would take the agent's allowed spending today above "
     f"${DAILY_CAP:,.0f}, it is blocked."),
    (7, "Needs customer confirmation", ASK,
     f"Every transfer, and any bill above ${CONFIRM_LIMIT:,.0f}, needs the "
     f"customer's confirmation."),
    (8, "Small bill", ALLOW,
     f"A bill payment of ${CONFIRM_LIMIT:,.0f} or less is allowed."),
]


@dataclass(frozen=True)
class Decision:
    decision: str   # ALLOW, ASK CUSTOMER or BLOCK
    rule: int       # which rule (1-8) caused it
    reason: str     # short explanation shown to the user and saved in the log


def parse_amount(text):
    """Turn user input like '120', '$1,250.50' into a number, or None if invalid."""
    if text is None:
        return None
    cleaned = str(text).strip().replace("$", "").replace(",", "")
    if cleaned == "":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def decide(agent_status, action, amount, spent_today=0.0):
    """
    agent_status : "unknown", "active" or "revoked" (looked up in the agents table)
    action       : e.g. "view_balance", "pay_bill", "transfer_money"
    amount       : number in USD, or None
    spent_today  : money this agent already moved today with ALLOW decisions
    """
    # Rule 1 - unknown agents are blocked
    if agent_status == "unknown":
        return Decision(BLOCK, 1, "Agent is not registered for this customer.")

    # Rule 2 - revoked agents are always blocked
    if agent_status == "revoked":
        return Decision(BLOCK, 2, "Agent's access has been revoked.")

    # Rule 3 - only the three bank actions are supported
    if action not in READ_ONLY_ACTIONS and action not in MONEY_ACTIONS:
        return Decision(BLOCK, 3, f"Action '{action}' is not supported.")

    # Rule 4 - read-only actions are allowed
    if action in READ_ONLY_ACTIONS:
        return Decision(ALLOW, 4, "Read-only action: no money moves.")

    # From here on the action moves money.
    # Rule 5 - the amount must be a real, positive number
    if amount is None or not math.isfinite(amount) or amount <= 0:
        return Decision(BLOCK, 5, "A money action needs a positive amount.")

    # Rule 6 - daily cap per agent
    if spent_today + amount > DAILY_CAP:
        return Decision(
            BLOCK, 6,
            f"Would take this agent's spending today to "
            f"${spent_today + amount:,.2f}, above the ${DAILY_CAP:,.2f} daily cap.")

    # Rule 7 - transfers always, and big bills, need the customer's yes
    if action == "transfer_money":
        return Decision(ASK, 7, "Transfers always need the customer's confirmation.")
    if amount > CONFIRM_LIMIT:
        return Decision(
            ASK, 7,
            f"Bill of ${amount:,.2f} is above the ${CONFIRM_LIMIT:,.2f} limit.")

    # Rule 8 - small bills are allowed
    return Decision(
        ALLOW, 8,
        f"Bill of ${amount:,.2f} is within the ${CONFIRM_LIMIT:,.2f} limit.")

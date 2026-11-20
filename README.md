# Agent Gatekeeper: JPMorgan Chase (prototype)

**Enrolment number:** PGD202571184

A small working prototype that sits between a bank customer's AI agent and the bank. Each agent request says who the customer is, which agent is asking, the action and the amount. The gatekeeper answers **ALLOW**, **ASK CUSTOMER** or **BLOCK**, and gives the rule number that caused the decision. Every decision is saved in an audit log with the date and time. You can register an agent and revoke it, and the revocation date and time are saved as proof (the "Wells Fargo problem").

The rules are in [RULES.md](RULES.md).

## What you need

- **Python 3.8 or newer.** Nothing else: the project uses only Python's built-in libraries.
- Check by opening a terminal (Windows: Command Prompt) and typing `python --version` (on Windows you can also try `py --version`).

## How to run it

1. Open a terminal in this project folder.
2. Run `python app.py` (Windows: `py app.py`).
3. Your browser opens at **http://127.0.0.1:8000**. If it doesn't, open that address yourself.
4. Click **Load demo agents**, then try requests in box 1.
5. Press **Ctrl + C** in the terminal to stop the app.

## How to run the automated tests

```
python -m unittest -v
```

This runs 14 tests: the six main test cases (TC1–TC6) and eight extra checks. All should say `ok`.

## Files

| File | What it does |
|------|--------------|
| `gatekeeper.py` | **The rules.** `decide()` checks rules 1–8 in order and returns the decision, rule number and reason. |
| `storage.py` | Saves agents and the audit log in a SQLite database file (`gatekeeper.db`), and handles register and revoke. |
| `app.py` | The web page: forms, rule list, agents table and audit log, plus CSV download. |
| `config.py` | Enrolment number and company name shown on screen. |
| `tests/test_gatekeeper.py` | Automated tests. |
| `RULES.md` | The rules (1 page) and the reason for the $500 limit. |
| `TEST_CASES.md` | The six test cases, with space for actual results. |
| `PROMPTS.md` | The instructions given to the AI coding tool, and the student's own checks. |

## How it works (in short)

1. You fill in box 1 and click **Check request**.
2. `app.py` passes the request to `storage.py`.
3. `storage.py` looks up the agent's status (unknown, active or revoked) and how much it has already spent today.
4. `gatekeeper.decide()` goes through rules 1–8 and stops at the first rule that matches.
5. The decision is written to the `audit_log` table with the date and time, and shown at the top of the page.

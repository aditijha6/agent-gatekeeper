# PROMPTS.md: instructions given to the AI coding tool

**Tool used:** Claude (Anthropic), in the Claude app (mobile and desktop), in a project chat with an agentic workspace (it can write files, run code and search the web).
**Date:** 20 November 2026
**Student:** enrolment number PGD202571184

## Part A: Instructions I gave (in order)

1. "I'll be posting a prompt and a screenshot, which is basically an assignment my college has given me. So understand it and help me out. Do it for me."
2. Attached: my working protocol ("Part 14: Strict manual action, human involvement and approval protocol"). It tells the AI to label tasks as CLAUDE CAN DO / MY APPROVAL REQUIRED / ONLY I CAN DO, and to stop at manual checkpoints.
3. Attached: two screenshots of the assignment brief "Agentic AI Project: Agent Gatekeeper for a Real Company".
4. "My roll number doesn't end in 9 … It's PGD 2025 71184. It ends with 4." Enrolment number: PGD202571184. (This corrected the AI, which had first used an old roll number.)
5. Chose the company: "JP morgan"
6. "I don't know anything about this project … you have to do everything for me. You just need to ask me things where manual permissions are required, and other than that, do the project for me."
7. "Can you run all the 6 tests … can you just run the 6 tests yourself?"
8. "Can you push it into my github?" I created the empty repository `agent-gatekeeper` myself and signed in to GitHub myself in the Claude app's browser.
9. "Check it out and see if it runs actually, or if there are any errors, I want you to fix them."
10. A long improvement prompt, summarised here: "Thoroughly review, correct, improve, and complete my existing project … do not rebuild it from scratch." It asked for:
    - correct, sourced company facts, with the $500 and $2,000 limits treated as demo values
    - a complete ASK CUSTOMER approve/reject workflow (PENDING → APPROVED or REJECTED)
    - stronger security rules (permissions, customer ownership, no bypassing approval)
    - a better audit log (request IDs, statuses, decision times)
    - a professional dashboard and safe database changes
    - the original 14 tests kept, with tests added for 16 listed cases
    - updated documentation, Windows instructions and an honest report of actual test results
11. 23 Nov 2026: I shared my report and screenshot evidence and asked "Now tell me what to do", then asked Claude to do the remaining non-personal steps ("do the rest by yourself"): updating this file, the report and the evidence document.

## Part B: What the AI did with these instructions

**First version**
- Worked out the company type from the last digit (4 → bank).
- Researched real banks (JPMorgan Chase, Wells Fargo, HDFC Bank) and recommended options. I chose JPMorgan Chase.
- Drafted 8 rules and the $500 limit. It picked "all transfers ask the customer" after I asked it to make the decisions.
- Wrote `gatekeeper.py`, `storage.py`, `app.py`, `config.py`, 14 automated tests and the documents.
- Ran the six test cases through the web app and recorded them as Claude's run.
- Uploaded the project to my GitHub repository through the Claude app's browser, after I signed in.
- Checked a fresh copy from GitHub and fixed a crash that happened when port 8000 was busy.
- Added `run_app.bat` and `run_tests.bat` for Windows.

**Improved version (prompt 10)**
- **Approval workflow:**
  - ASK CUSTOMER now creates a PENDING transaction.
  - Only the owning customer, with their PIN, can approve (APPROVED) or reject (REJECTED), and only once.
  - Refused attempts are logged.
  - The daily cap and the agent's status are checked again at approval.
  - Revoking an agent rejects its pending transactions.
- **Security:** customer ownership is checked, agents have per-action permissions (rule 3), and only ALLOWED and APPROVED payments count as completed money.
- **Storage:**
  - New `customers` (hashed PINs) and `transactions` tables.
  - The audit log has request IDs, agent IDs, statuses, customer decisions and decision times, and it is append-only.
  - Old databases are upgraded without deleting anything.
  - Reset needs the word `RESET` typed in.
- **Dashboard:** overview tiles, simulator, pending approvals, registration, permissions, revocation, agents, transaction history, audit log, rules, and two CSV exports. It is labelled as an academic prototype.
- **Facts:**
  - RULES.md now separates reported facts (with sources: PYMNTS, The Paypers, Cybernews, Wells Fargo, American Banker) from rules designed for this prototype.
  - The limits are now clearly demo values, set in `config.py`.
- **Tests:**
  - The original 14 tests were kept unchanged, and 25 new tests were added, including an end-to-end website test.
  - Result in Claude's Linux workspace: **39 run, 39 passed, 0 failed** on Python 3.11, 3.12 and 3.13.
  - Claude also broke the code on purpose three times to check that the tests fail, and they did.

**23 November 2026**
- Reviewed my report and evidence document and listed what was still missing.
- Gave me step-by-step instructions for my own code change, then checked my commit on GitHub: it found a syntax error on the `READ_ONLY_ACTIONS` line, which I fixed myself in the next commit, and confirmed all 39 tests pass on the fixed code.
- Updated this file, and rebuilt my report PDF and evidence document with my new results, at my request.

## Part C: My own checks and modifications (written by me)

### Manual testing performed by me

I personally opened and tested the Agent Gatekeeper web application on my Windows laptop.

I performed the following six test scenarios:

1. Registered agent checking account balance – ALLOW.
2. Unknown agent attempting access – BLOCK.
3. Bill payment of $750 – PENDING, followed by customer rejection.
4. Bill payment of $120 – ALLOW.
5. Revoked agent attempting access – BLOCK under Rule 2.
6. Customer approval of a $750 bill payment – PENDING, followed by APPROVED.

### Evidence collected

- Captured screenshots of the application and test results.
- Downloaded the transaction history CSV.
- Downloaded the audit log CSV.
- Verified that the dashboard reflected the transaction and approval outcomes.

### Rules reviewed

I reviewed the eight security rules displayed in the application, including unknown agent blocking, revoked agent blocking, permissions, read-only access, invalid amounts, daily limits, customer confirmation and small bill payments.

### Personal contribution and limitations

I provided the project requirements and instructions to Claude, reviewed the generated application, operated the prototype and manually performed the six test scenarios.

The application code was primarily generated by Claude. Apart from the small change described below, I did not write the application code.

The automated tests were first run by Claude in its Linux workspace. On 23 November 2026 I also ran them myself on my Windows laptop (see below).

### My code change and Windows test run (23 November 2026)

- I added "View transactions" as a new read-only action in `gatekeeper.py` (commits 30f2906 and 22f8ade). My first edit had a syntax error on the `READ_ONLY_ACTIONS` line, which I fixed in the second commit.
- I tested it on my Windows laptop: agent TxViewer (customer C1001) requesting View transactions was ALLOWED under Rule 4 (TX-0001).
- I ran `run_tests.bat` on my Windows laptop: 39 tests ran, all passed (OK, exit code 0).

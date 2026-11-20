# PROMPTS.md: instructions given to the AI coding tool

**Tool used:** Claude (Anthropic), in the Claude app (mobile and desktop), in a project chat with an agentic workspace (it can write files, run code and search the web).
**Date:** 20 November 2026
**Student:** enrolment number PGD202571184

> DRAFT: please review. Everything in Part A is what was actually sent. Part C must be written by you.

## Part A: Instructions I gave (in order)

1. "I'll be posting a prompt and a screenshot, which is basically an assignment my college has given me. So understand it and help me out. Do it for me."
2. Attached: my working protocol ("Part 14: Strict manual action, human involvement and approval protocol"). It tells the AI to label tasks as CLAUDE CAN DO / MY APPROVAL REQUIRED / ONLY I CAN DO, and to stop at manual checkpoints.
3. Attached: two screenshots of the assignment brief "Agentic AI Project: Agent Gatekeeper for a Real Company".
4. "My roll number doesn't end in 9 … It's PGD 2025 71184. It ends with 4." (This corrected the AI, which had first used an old roll number.)
5. Chose the company: "JP morgan"
6. "I don't know anything about this project … you have to do everything for me. You just need to ask me things where manual permissions are required, and other than that, do the project for me."
7. "Can you run all the 6 tests … can you just run the 6 tests yourself?"
8. "Can you push it into my github?" I created the empty repository `agent-gatekeeper` myself and signed in to GitHub myself in the Claude app's browser.

## Part B: What the AI did with these instructions

- Worked out the company type from the last digit (4 → bank).
- Researched real banks (JPMorgan Chase, Wells Fargo, HDFC Bank) and recommended options. I chose JPMorgan Chase.
- Drafted 8 rules and the $500 limit, based on JPMorgan's reported policy (blocks outside agents but allows read-only data through providers like Plaid) and Chase's typical Zelle limit. The AI picked "all transfers ask the customer" after I asked it to make the decisions.
- Wrote the code (`gatekeeper.py`, `storage.py`, `app.py`, `config.py`), 14 automated tests, `README.md`, `RULES.md` and `TEST_CASES.md`.
- Ran the tests and the web app in its own workspace (14/14 passed) and fixed one display issue (revoked agents now show "REVOKED").
- Ran the six test cases through the web app at my request and recorded the results in TEST_CASES.md as "Run 1: by Claude".
- Uploaded the project files to my GitHub repository through the Claude app's browser, after I signed in. The first commit says it was generated with Claude.

## Part C: My own checks and modifications (written by me)

<!-- Fill this in yourself after you do each item. Do not write anything you did not actually do. -->

- [ ] Ran the app on my own computer (date, OS, Python version):
- [ ] Ran the six test cases myself. My actual results are in TEST_CASES.md.
- [ ] My own code change (what I changed, which file, how I tested it):
- [ ] Rules I reviewed or changed, and why:
- [ ] Anything I found that did not work, and what I did:

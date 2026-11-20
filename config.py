"""
Project settings shown on screen. Change these if any detail is wrong.

This is an academic prototype based on JPMorgan Chase. It is NOT an official
JPMorgan Chase product and is not connected to any real banking system.
"""

ENROLMENT_NUMBER = "PGD202571184"
COMPANY = "JPMorgan Chase"
PROJECT_TITLE = "Agent Gatekeeper"
CURRENCY = "USD"

# ---- Demonstration limits (US dollars) -------------------------------------
# These are values chosen for THIS prototype. They are NOT official JPMorgan
# Chase limits. Change them here and the rules, screen and tests follow.
#
# CONFIRM_LIMIT: bill payments above this need the customer's approval.
#   Chosen as a quarter of the ~$2,000/day Zelle limit that third-party sites
#   (e.g. Wise) report for Chase personal checking accounts.
CONFIRM_LIMIT = 500.00
#
# DAILY_CAP: the most money one agent may move for one customer in one day
#   (counting only completed payments: ALLOWED and APPROVED).
DAILY_CAP = 2000.00

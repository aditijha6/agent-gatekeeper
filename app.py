"""
Agent Gatekeeper - web dashboard (academic prototype based on JPMorgan Chase).

Run:   python app.py        (Windows: py app.py, or double-click run_app.bat)
Open:  http://127.0.0.1:8000

Uses only Python's standard library, so there is nothing to install.
"""

import argparse
import html
import os
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import config
import gatekeeper as gk
from storage import Store, now_text, parse_request_label, request_label

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = None            # set in main() (or by the tests)
LAST_RESULT = None      # (kind, html) message shown after the last button press

STATUS_CSS = {gk.ALLOWED: "allow", gk.APPROVED: "approve", gk.PENDING: "ask",
              gk.BLOCKED: "block", gk.REJECTED: "reject"}
DECISION_CSS = {gk.ALLOW: "allow", gk.ASK: "ask", gk.BLOCK: "block"}


def esc(value):
    return html.escape("" if value is None else str(value))


def money(v):
    return "-" if v is None else f"${v:,.2f}"


def badge(text, css):
    return f'<span class="badge {css}">{esc(text)}</span>'


def status_badge(status):
    return badge(status, STATUS_CSS.get(status, "info")) if status else "-"


def decision_badge(decision):
    return badge(decision, DECISION_CSS.get(decision, "info")) if decision else "-"


def agent_badge(revoked_at):
    return badge("REVOKED", "block") if revoked_at else badge("ACTIVE", "allow")


def action_label(action):
    return gk.ACTION_LABELS.get(action, action or "-")


def permission_boxes(checked):
    return "".join(
        f'<label class="check"><input type="checkbox" name="perm" value="{k}"'
        f'{" checked" if k in checked else ""}> {esc(v)}</label>'
        for k, v in gk.ACTION_LABELS.items())


# ---------------------------------------------------------------- page parts

def render_stats():
    s = STORE.stats(now_text()[:10])
    c = s["counts"]
    tiles = [
        ("Active agents", s["active_agents"], ""), ("Revoked agents", s["revoked_agents"], ""),
        ("Pending approvals", c[gk.PENDING], "ask"), ("Allowed today", c[gk.ALLOWED], "allow"),
        ("Approved today", c[gk.APPROVED], "approve"), ("Rejected today", c[gk.REJECTED], "reject"),
        ("Blocked today", c[gk.BLOCKED], "block"),
        ("Money completed today", money(s["completed_money"]), ""),
    ]
    return "".join(f'<div class="tile {css}"><div class="num">{esc(v)}</div>'
                   f'<div class="lbl">{esc(k)}</div></div>' for k, v, css in tiles)


def render_pending():
    rows = STORE.pending_transactions()
    if not rows:
        return '<p class="muted">No transactions are waiting for the customer.</p>'
    out = []
    for t in rows:
        label = request_label(t["id"])
        out.append(f"""
        <div class="pending">
          <div><b>{label}</b> · {badge("PENDING", "ask")} · requested {esc(t['created_at'])}</div>
          <div class="big">{esc(t['agent_name'])} wants to <b>{esc(action_label(t['action']).lower())}</b>
               of <b>{money(t['amount'])}</b> for customer <b>{esc(t['customer'])}</b></div>
          <div class="muted">Rule {esc(t['rule'])}: {esc(t['reason'])}</div>
          <form method="post" action="/decision" class="inline">
            <input type="hidden" name="tx" value="{label}">
            <input name="customer" placeholder="Customer ID" required>
            <input name="pin" type="password" placeholder="Customer PIN" required>
            <button name="choice" value="approve" class="ok">Approve</button>
            <button name="choice" value="reject" class="danger">Reject</button>
          </form>
        </div>""")
    return "".join(out)


def render_agents():
    rows = "".join(
        f"<tr><td>AG-{a['id']:03d}</td><td>{esc(a['customer'])}</td><td>{esc(a['agent_name'])}</td>"
        f"<td>{esc(', '.join(action_label(p) for p in sorted(gk.parse_permissions(a['permissions']))))}</td>"
        f"<td>{esc(a['registered_at'])}</td><td>{agent_badge(a['revoked_at'])}</td>"
        f"<td>{esc(a['revoked_at'] or '-')}</td></tr>"
        for a in STORE.list_agents())
    return rows or '<tr><td colspan="7">No agents yet. Click "Load demo agents" or register one.</td></tr>'


def render_transactions():
    rows = "".join(
        f"<tr><td>{request_label(t['id'])}</td><td>{esc(t['created_at'])}</td>"
        f"<td>{esc(t['customer'])}</td><td>{esc(t['agent_name'])}</td>"
        f"<td>{esc(action_label(t['action']))}</td><td>{money(t['amount'])}</td>"
        f"<td>{esc(t['rule'])}</td><td>{status_badge(t['status'])}</td>"
        f"<td>{esc(t['decided_by'] or '-')}</td><td>{esc(t['decided_at'] or '-')}</td>"
        f"<td>{esc(t['reason'])}</td></tr>"
        for t in STORE.transactions())
    return rows or '<tr><td colspan="11">No transactions yet.</td></tr>'


def render_audit():
    rows = "".join(
        f"<tr><td>{esc(r['logged_at'])}</td><td>{esc(r['event'])}</td>"
        f"<td>{esc(r['request_id'] or '-')}</td><td>{esc(r['customer'] or '-')}</td>"
        f"<td>{esc(r['agent_name'] or '-')}</td><td>{esc(r['action'] or '-')}</td>"
        f"<td>{money(r['amount'])}</td><td>{esc(r['rule'] or '-')}</td>"
        f"<td>{decision_badge(r['decision'])}</td><td>{status_badge(r['status'])}</td>"
        f"<td>{esc(r['customer_decision'] or '-')}</td><td>{esc(r['decided_at'] or '-')}</td>"
        f"<td>{esc(r['reason'])}</td></tr>"
        for r in STORE.audit_rows())
    return rows or '<tr><td colspan="13">The log is empty.</td></tr>'


def render_page():
    banner = ""
    if LAST_RESULT:
        kind, text = LAST_RESULT
        banner = f'<div id="result" class="banner {kind}">{text}</div>'

    rules_html = "".join(
        f"<li><b>Rule {n}: {esc(name)}</b> → {decision_badge(dec)}<br><small>{esc(desc)}</small></li>"
        for n, name, dec, desc in gk.RULES)
    options = "".join(f'<option value="{k}">{esc(v)}</option>' for k, v in gk.ACTION_LABELS.items())
    options += '<option value="close_account">Close account (not supported)</option>'
    customers = STORE.list_customers()
    customer_options = "".join(f'<option value="{esc(c["customer_id"])}">{esc(c["customer_id"])} – {esc(c["name"])}</option>'
                               for c in customers)
    customer_list = "".join(f'<option value="{esc(c["customer_id"])}">' for c in customers)

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(config.PROJECT_TITLE)} – {esc(config.COMPANY)} (academic prototype)</title>
<style>
  body {{ font-family: system-ui, Segoe UI, Arial, sans-serif; margin: 0; background: #f2f4f7; color: #1d2733; }}
  header {{ background: #0b3a66; color: #fff; padding: 14px 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }}
  header h1 {{ margin: 0; font-size: 21px; }} header .sub {{ font-size: 12px; opacity: .85; }}
  .enrol {{ background: #fff; color: #0b3a66; padding: 6px 12px; border-radius: 6px; font-weight: 700; }}
  nav {{ background: #fff; border-bottom: 1px solid #dde3ea; padding: 8px 24px; position: sticky; top: 0; z-index: 2; }}
  nav a {{ margin-right: 16px; color: #0b3a66; text-decoration: none; font-size: 14px; font-weight: 600; }}
  main {{ max-width: 1280px; margin: 0 auto; padding: 18px 20px 40px; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  .card {{ background: #fff; border-radius: 10px; padding: 16px 20px; box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 16px; }}
  h2 {{ font-size: 17px; margin: 0 0 12px; }} h3 {{ font-size: 14px; margin: 14px 0 6px; }}
  label {{ display: block; font-size: 13px; margin: 8px 0 3px; color: #455; }}
  label.check {{ display: inline-block; margin-right: 14px; color: #1d2733; }}
  input, select {{ width: 100%; box-sizing: border-box; padding: 8px; border: 1px solid #c4ccd4; border-radius: 6px; font-size: 14px; }}
  input[type=checkbox] {{ width: auto; }}
  form.inline {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }}
  form.inline input {{ width: 150px; }} form.inline button {{ margin-top: 0; }}
  button {{ margin-top: 12px; padding: 9px 16px; border: 0; border-radius: 6px; background: #0b3a66; color: #fff; font-size: 14px; cursor: pointer; }}
  button.secondary {{ background: #6b7785; }} button.danger {{ background: #b3261e; }} button.ok {{ background: #1e8e3e; }}
  .banner {{ padding: 14px 18px; border-radius: 8px; margin-bottom: 16px; font-size: 16px; }}
  .banner.allow, .banner.approve {{ background: #e3f6e8; border-left: 6px solid #1e8e3e; }}
  .banner.ask {{ background: #fff4dc; border-left: 6px solid #d18f00; }}
  .banner.block {{ background: #fde7e6; border-left: 6px solid #b3261e; }}
  .banner.reject {{ background: #eceff3; border-left: 6px solid #5f6b7a; }}
  .banner.info {{ background: #e6f0fb; border-left: 6px solid #0b3a66; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 700; color: #fff; white-space: nowrap; background: #6b7785; }}
  .badge.allow {{ background: #1e8e3e; }} .badge.approve {{ background: #0f6b2e; }} .badge.ask {{ background: #d18f00; }}
  .badge.block {{ background: #b3261e; }} .badge.reject {{ background: #5f6b7a; }}
  .tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; }}
  .tile {{ background: #f7f9fb; border-radius: 8px; padding: 10px 12px; border-top: 4px solid #c4ccd4; }}
  .tile.allow {{ border-color: #1e8e3e; }} .tile.approve {{ border-color: #0f6b2e; }} .tile.ask {{ border-color: #d18f00; }}
  .tile.block {{ border-color: #b3261e; }} .tile.reject {{ border-color: #5f6b7a; }}
  .tile .num {{ font-size: 22px; font-weight: 700; }} .tile .lbl {{ font-size: 12px; color: #556; }}
  .pending {{ border: 1px solid #f0d9a6; background: #fffaf0; border-radius: 8px; padding: 10px 12px; margin-bottom: 10px; }}
  .pending .big {{ margin: 6px 0; }}
  .muted {{ color: #667; font-size: 13px; }}
  ol.rules {{ padding-left: 0; margin: 0; }} ol.rules li {{ list-style: none; margin-bottom: 8px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid #e3e7eb; vertical-align: top; }}
  th {{ background: #eef2f6; position: sticky; top: 0; }}
  .scroll {{ overflow: auto; max-height: 420px; }}
  .row {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: end; }}
  .row form {{ margin: 0; }}
</style></head>
<body>
<header>
  <div><h1>{esc(config.PROJECT_TITLE)} · {esc(config.COMPANY)}</h1>
  <div class="sub">Academic prototype – not an official JPMorgan Chase product and not connected to any real bank.</div></div>
  <div class="enrol">Enrolment number: {esc(config.ENROLMENT_NUMBER)}</div>
</header>
<nav>
  <a href="#overview">Overview</a><a href="#simulator">Simulator</a><a href="#approvals">Approvals</a>
  <a href="#agents">Agents</a><a href="#history">Transactions</a><a href="#audit">Audit log</a><a href="#rules">Rules &amp; tools</a>
</nav>
<main>
{banner}
<div class="card" id="overview">
  <h2>Dashboard overview</h2>
  <div class="tiles">{render_stats()}</div>
  <p class="muted">Demonstration limits (set in config.py, not official JPMorgan Chase limits):
  bills above <b>{money(gk.CONFIRM_LIMIT)}</b> and all transfers need the customer's approval;
  one agent may complete at most <b>{money(gk.DAILY_CAP)}</b> per customer per day.</p>
</div>

<div class="grid">
  <div class="card" id="simulator">
    <h2>Transaction simulator (an AI agent sends a request)</h2>
    <form method="post" action="/check">
      <label>Customer ID</label><input name="customer" list="customers" placeholder="e.g. C1001" required>
      <datalist id="customers">{customer_list}</datalist>
      <label>Agent name</label><input name="agent" placeholder="e.g. BudgetBot">
      <label>Action</label><select name="action">{options}</select>
      <label>Amount ({esc(config.CURRENCY)}) – leave empty for View balance</label>
      <input name="amount" placeholder="e.g. 120">
      <button type="submit">Check request</button>
    </form>
  </div>
  <div class="card" id="approvals">
    <h2>Pending customer approvals</h2>
    <p class="muted">Only the customer who owns the transaction can decide, using their PIN.
    An agent cannot approve its own request. Each transaction can be decided only once.</p>
    {render_pending()}
  </div>
</div>

<div class="grid" id="agents">
  <div class="card">
    <h2>Agent registration</h2>
    <form method="post" action="/register">
      <label>Customer</label><select name="customer">{customer_options}</select>
      <label>Agent name</label><input name="agent" required>
      <label>Permissions</label>{permission_boxes(gk.ALL_ACTIONS)}
      <br><button type="submit">Register agent</button>
    </form>
  </div>
  <div class="card">
    <h2>Agent permissions</h2>
    <form method="post" action="/permissions">
      <div class="row"><div style="flex:1"><label>Customer ID</label><input name="customer" required></div>
      <div style="flex:1"><label>Agent name</label><input name="agent" required></div></div>
      <label>New permissions</label>{permission_boxes({"view_balance"})}
      <br><button type="submit" class="secondary">Update permissions</button>
    </form>
    <h3>Agent revocation</h3>
    <form method="post" action="/revoke">
      <div class="row"><div style="flex:1"><label>Customer ID</label><input name="customer" required></div>
      <div style="flex:1"><label>Agent name</label><input name="agent" required></div></div>
      <button type="submit" class="danger">Revoke agent</button>
    </form>
  </div>
</div>

<div class="card scroll">
  <h2>Registered agents</h2>
  <table><tr><th>Agent ID</th><th>Customer</th><th>Agent</th><th>Permissions</th><th>Registered at</th><th>Status</th><th>Revoked at</th></tr>
  {render_agents()}</table>
</div>

<div class="card scroll" id="history">
  <h2>Transaction history (current status)</h2>
  <table><tr><th>Request ID</th><th>Requested at</th><th>Customer</th><th>Agent</th><th>Action</th><th>Amount</th>
  <th>Rule</th><th>Status</th><th>Decided by</th><th>Decided at</th><th>Reason</th></tr>
  {render_transactions()}</table>
</div>

<div class="card scroll" id="audit">
  <h2>Audit log (every event, newest first – never edited)</h2>
  <table><tr><th>Date &amp; time</th><th>Event</th><th>Request ID</th><th>Customer</th><th>Agent</th><th>Action</th>
  <th>Amount</th><th>Rule</th><th>Decision</th><th>Status</th><th>Customer decision</th><th>Decided at</th><th>Reason</th></tr>
  {render_audit()}</table>
</div>

<div class="grid" id="rules">
  <div class="card">
    <h2>Security rules (checked in order – first match wins)</h2>
    <ol class="rules">{rules_html}</ol>
  </div>
  <div class="card">
    <h2>Demo tools and CSV export</h2>
    <div class="row">
      <form method="post" action="/demo"><button class="secondary">Load demo agents</button></form>
      <form method="get" action="/transactions.csv"><button class="secondary">Download transactions (CSV)</button></form>
      <form method="get" action="/audit.csv"><button class="secondary">Download audit log (CSV)</button></form>
    </div>
    <h3>Demo customers (fictional)</h3>
    <p class="muted">C1001 Asha Verma – PIN 1111 · C1002 Rahul Mehta – PIN 2222 · C1003 Neha Kapoor – PIN 3333<br>
    Demo agents: C1001 / BudgetBot (all permissions), C1001 / ShopperGPT (revoked),
    C1002 / FinanceBuddy (view balance only).</p>
    <h3>Reset demo data</h3>
    <form method="post" action="/reset" class="inline">
      <input name="confirm" placeholder="Type RESET">
      <button class="danger">Delete agents, transactions and log</button>
    </form>
  </div>
</div>
</main></body></html>"""


# ---------------------------------------------------------------- web server

class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, content_type="text/html; charset=utf-8", extra=None):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, anchor="result"):
        self.send_response(303)
        self.send_header("Location", f"/#{anchor}")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, render_page())
        elif path == "/audit.csv":
            self._send(200, STORE.export_audit_csv(), "text/csv; charset=utf-8",
                       {"Content-Disposition": "attachment; filename=audit_log.csv"})
        elif path == "/transactions.csv":
            self._send(200, STORE.export_transactions_csv(), "text/csv; charset=utf-8",
                       {"Content-Disposition": "attachment; filename=transactions.csv"})
        else:
            self._send(404, "Not found", "text/plain")

    def do_POST(self):
        global LAST_RESULT
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = parse_qs(self.rfile.read(length).decode("utf-8"))
        form = {k: v[0] for k, v in raw.items()}
        perms = set(raw.get("perm", []))
        path = urlparse(self.path).path

        if path == "/check":
            result, tx = STORE.check_request(form.get("customer"), form.get("agent"),
                                             form.get("action"), form.get("amount"))
            label = request_label(tx["id"])
            extra = (" Waiting for the customer: see <a href='#approvals'>Pending customer approvals</a>."
                     if result.status == gk.PENDING else "")
            LAST_RESULT = (STATUS_CSS[result.status],
                           f"<b>{esc(result.status)}</b> ({esc(result.decision)}) &nbsp;·&nbsp; Rule {result.rule}"
                           f" &nbsp;·&nbsp; {esc(result.reason)} <small>({label}, {esc(tx['created_at'])})</small>{extra}")
        elif path == "/decision":
            approve = form.get("choice") == "approve"
            ok, msg = STORE.customer_decision(form.get("tx"), form.get("customer"), form.get("pin"), approve)
            tx_id = parse_request_label(form.get("tx"))
            tx = STORE.get_transaction(tx_id) if tx_id else None
            status = tx["status"] if (ok and tx) else None
            LAST_RESULT = (STATUS_CSS.get(status, "block"), esc(msg))
        elif path == "/register":
            ok, msg = STORE.register_agent(form.get("customer"), form.get("agent"), perms)
            LAST_RESULT = ("info" if ok else "block", esc(msg))
        elif path == "/permissions":
            ok, msg = STORE.update_permissions(form.get("customer"), form.get("agent"), perms)
            LAST_RESULT = ("info" if ok else "block", esc(msg))
        elif path == "/revoke":
            ok, msg = STORE.revoke_agent(form.get("customer"), form.get("agent"))
            LAST_RESULT = ("info" if ok else "block", esc(msg))
        elif path == "/demo":
            STORE.load_demo_data()
            LAST_RESULT = ("info", "Demo agents loaded (agents that already exist were left as they were).")
        elif path == "/reset":
            ok, msg = STORE.reset(form.get("confirm", ""))
            LAST_RESULT = ("info" if ok else "block", esc(msg))
        else:
            self._send(404, "Not found", "text/plain")
            return
        self._redirect()

    def log_message(self, fmt, *args):
        pass  # keep the terminal quiet


def main():
    global STORE
    parser = argparse.ArgumentParser(description="Agent Gatekeeper prototype")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default=os.path.join(HERE, "gatekeeper.db"))
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    STORE = Store(args.db)

    # If the port is busy (e.g. the app is already running), try the next ones.
    server = None
    for port in range(args.port, args.port + 10):
        try:
            server = HTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            print(f"Port {port} is busy, trying {port + 1}...")
    if server is None:
        print("No free port found. Close other copies of the app and try again.")
        return

    url = f"http://127.0.0.1:{port}"
    print(f"{config.PROJECT_TITLE} for {config.COMPANY} is running at {url}")
    print("Keep this window open while you use the app. Press Ctrl+C (or close it) to stop.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()

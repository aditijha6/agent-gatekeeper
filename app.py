"""
Agent Gatekeeper - web screen.

Run:   python app.py        (Windows: py app.py)
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
from storage import Store

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = None            # set in main()
LAST_RESULT = None      # the message shown after the last button press


def esc(value):
    return html.escape("" if value is None else str(value))


def badge(decision):
    css = {gk.ALLOW: "allow", gk.ASK: "ask", gk.BLOCK: "block"}.get(decision, "info")
    return f'<span class="badge {css}">{esc(decision)}</span>'


def status_badge(revoked_at):
    if revoked_at:
        return '<span class="badge block">REVOKED</span>'
    return '<span class="badge allow">ACTIVE</span>'


def render_page():
    # ----- result banner -----
    banner = ""
    if LAST_RESULT:
        kind, text = LAST_RESULT
        banner = f'<div id="result" class="banner {kind}">{text}</div>'

    # ----- rules list -----
    rules_html = "".join(
        f"<li><b>Rule {n}: {esc(name)}</b> → {badge(dec)}<br><small>{esc(desc)}</small></li>"
        for n, name, dec, desc in gk.RULES)

    # ----- action dropdown -----
    options = "".join(f'<option value="{k}">{esc(v)}</option>'
                      for k, v in gk.ACTION_LABELS.items())
    options += '<option value="close_account">Close account (not supported)</option>'

    # ----- agents table -----
    agent_rows = "".join(
        f"<tr><td>{esc(a['customer'])}</td><td>{esc(a['agent_name'])}</td>"
        f"<td>{esc(a['registered_at'])}</td>"
        f"<td>{status_badge(a['revoked_at'])}</td>"
        f"<td>{esc(a['revoked_at'] or '-')}</td></tr>"
        for a in STORE.list_agents()) or '<tr><td colspan="5">No agents yet.</td></tr>'

    # ----- audit log table -----
    def amount_cell(v):
        return "-" if v is None else f"${v:,.2f}"

    log_rows = "".join(
        f"<tr><td>{esc(r['logged_at'])}</td><td>{esc(r['event'])}</td>"
        f"<td>{esc(r['customer'])}</td><td>{esc(r['agent_name'])}</td>"
        f"<td>{esc(r['action'] or '-')}</td><td>{amount_cell(r['amount'])}</td>"
        f"<td>{badge(r['decision']) if r['decision'] else '-'}</td>"
        f"<td>{esc(r['rule'] or '-')}</td><td>{esc(r['reason'])}</td></tr>"
        for r in STORE.audit_rows()) or '<tr><td colspan="9">The log is empty.</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(config.PROJECT_TITLE)} – {esc(config.COMPANY)}</title>
<style>
  body {{ font-family: system-ui, Segoe UI, Arial, sans-serif; margin: 0; background: #f4f6f8; color: #1d2733; }}
  header {{ background: #0b3a66; color: #fff; padding: 16px 24px; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; }}
  header h1 {{ margin: 0; font-size: 22px; }}
  .enrol {{ background: #fff; color: #0b3a66; padding: 6px 12px; border-radius: 6px; font-weight: 700; }}
  main {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  @media (max-width: 800px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  .card {{ background: #fff; border-radius: 10px; padding: 16px 20px; box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 16px; }}
  h2 {{ font-size: 17px; margin: 0 0 12px; }}
  label {{ display: block; font-size: 13px; margin: 8px 0 3px; color: #455; }}
  input, select {{ width: 100%; box-sizing: border-box; padding: 8px; border: 1px solid #c4ccd4; border-radius: 6px; font-size: 14px; }}
  button {{ margin-top: 12px; padding: 9px 16px; border: 0; border-radius: 6px; background: #0b3a66; color: #fff; font-size: 14px; cursor: pointer; }}
  button.secondary {{ background: #6b7785; }}
  button.danger {{ background: #b3261e; }}
  .banner {{ padding: 14px 18px; border-radius: 8px; margin-bottom: 16px; font-size: 16px; }}
  .banner.allow {{ background: #e3f6e8; border-left: 6px solid #1e8e3e; }}
  .banner.ask {{ background: #fff4dc; border-left: 6px solid #d18f00; }}
  .banner.block {{ background: #fde7e6; border-left: 6px solid #b3261e; }}
  .banner.info {{ background: #e6f0fb; border-left: 6px solid #0b3a66; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 700; color: #fff; white-space: nowrap; }}
  .badge.allow {{ background: #1e8e3e; }} .badge.ask {{ background: #d18f00; }} .badge.block {{ background: #b3261e; }}
  ol.rules {{ padding-left: 18px; margin: 0; }} ol.rules li {{ list-style: none; margin-bottom: 8px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid #e3e7eb; vertical-align: top; }}
  th {{ background: #eef2f6; }}
  .scroll {{ overflow-x: auto; }}
  .row {{ display: flex; gap: 8px; flex-wrap: wrap; }}
</style></head>
<body>
<header>
  <h1>{esc(config.PROJECT_TITLE)} · {esc(config.COMPANY)} (prototype)</h1>
  <div class="enrol">Enrolment number: {esc(config.ENROLMENT_NUMBER)}</div>
</header>
<main>
{banner}
<div class="grid">
  <div>
    <div class="card">
      <h2>1. Agent request</h2>
      <form method="post" action="/check">
        <label>Customer ID</label><input name="customer" placeholder="e.g. C1001" required>
        <label>Agent name</label><input name="agent" placeholder="e.g. BudgetBot">
        <label>Action</label><select name="action">{options}</select>
        <label>Amount ({esc(config.CURRENCY)}) – leave empty for View balance</label>
        <input name="amount" placeholder="e.g. 120">
        <button type="submit">Check request</button>
      </form>
    </div>
    <div class="card">
      <h2>2. Register an agent</h2>
      <form method="post" action="/register">
        <label>Customer ID</label><input name="customer" required>
        <label>Agent name</label><input name="agent" required>
        <button type="submit">Register agent</button>
      </form>
    </div>
    <div class="card">
      <h2>3. Revoke an agent</h2>
      <form method="post" action="/revoke">
        <label>Customer ID</label><input name="customer" required>
        <label>Agent name</label><input name="agent" required>
        <button type="submit" class="danger">Revoke agent</button>
      </form>
    </div>
  </div>
  <div>
    <div class="card">
      <h2>Rules (checked in order – first match wins)</h2>
      <ol class="rules">{rules_html}</ol>
    </div>
    <div class="card">
      <h2>Demo tools</h2>
      <div class="row">
        <form method="post" action="/demo"><button class="secondary">Load demo agents</button></form>
        <form method="get" action="/audit.csv"><button class="secondary">Download audit log (CSV)</button></form>
        <form method="post" action="/reset" onsubmit="return confirm('Delete all agents and the whole audit log?');">
          <button class="danger">Reset all data</button></form>
      </div>
      <p><small>Demo agents: <b>C1001 / BudgetBot</b> (active), <b>C1001 / ShopperGPT</b> (revoked),
      <b>C1002 / FinanceBuddy</b> (active).</small></p>
    </div>
  </div>
</div>
<div class="card scroll">
  <h2>Registered agents</h2>
  <table><tr><th>Customer</th><th>Agent</th><th>Registered at</th><th>Status</th><th>Revoked at</th></tr>
  {agent_rows}</table>
</div>
<div class="card scroll">
  <h2>Audit log (newest first)</h2>
  <table><tr><th>Date &amp; time</th><th>Event</th><th>Customer</th><th>Agent</th><th>Action</th>
  <th>Amount</th><th>Decision</th><th>Rule</th><th>Reason</th></tr>
  {log_rows}</table>
</div>
</main></body></html>"""


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

    def _redirect_home(self):
        self.send_response(303)
        self.send_header("Location", "/#result")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, render_page())
        elif path == "/audit.csv":
            self._send(200, STORE.export_csv(), "text/csv; charset=utf-8",
                       {"Content-Disposition": "attachment; filename=audit_log.csv"})
        else:
            self._send(404, "Not found", "text/plain")

    def do_POST(self):
        global LAST_RESULT
        length = int(self.headers.get("Content-Length", 0) or 0)
        form = {k: v[0] for k, v in parse_qs(self.rfile.read(length).decode("utf-8")).items()}
        path = urlparse(self.path).path

        if path == "/check":
            result, when = STORE.check_request(form.get("customer"), form.get("agent"),
                                               form.get("action"), form.get("amount"))
            kind = {gk.ALLOW: "allow", gk.ASK: "ask", gk.BLOCK: "block"}[result.decision]
            LAST_RESULT = (kind, f"<b>{esc(result.decision)}</b> &nbsp;·&nbsp; Rule {result.rule}"
                                 f" &nbsp;·&nbsp; {esc(result.reason)} <small>({esc(when)})</small>")
        elif path == "/register":
            ok, msg = STORE.register_agent(form.get("customer"), form.get("agent"))
            LAST_RESULT = ("info" if ok else "block", esc(msg))
        elif path == "/revoke":
            ok, msg = STORE.revoke_agent(form.get("customer"), form.get("agent"))
            LAST_RESULT = ("info" if ok else "block", esc(msg))
        elif path == "/demo":
            STORE.load_demo_data()
            LAST_RESULT = ("info", "Demo agents loaded.")
        elif path == "/reset":
            STORE.reset()
            LAST_RESULT = ("info", "All agents and the audit log were deleted.")
        else:
            self._send(404, "Not found", "text/plain")
            return
        self._redirect_home()

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
    url = f"http://127.0.0.1:{args.port}"
    server = HTTPServer(("127.0.0.1", args.port), Handler)
    print(f"{config.PROJECT_TITLE} for {config.COMPANY} is running at {url}")
    print("Press Ctrl+C to stop.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()

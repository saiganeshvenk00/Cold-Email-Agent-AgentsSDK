import os
import asyncio
from typing import Dict, Optional, Set, List, Any
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content, Header
from agent_sdk import function_tool
from fastapi import FastAPI, Request, UploadFile, File, WebSocket, WebSocketDisconnect
import uvicorn
from dotenv import load_dotenv
from thread_store import record_inbound_message
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import csv
import tempfile
from cold_pipeline.workflow import run_cold_workflow, run_cold_workflow_bulk

# Load environment variables for local/dev runs
load_dotenv()

# Create a FastAPI application instance
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket clients registry
_ws_clients: Set[WebSocket] = set()

async def _broadcast(event: Dict[str, Any]) -> None:
    if not _ws_clients:
        return
    stale: List[WebSocket] = []
    for ws in list(_ws_clients):
        try:
            await ws.send_json(event)
        except Exception:
            stale.append(ws)
    for ws in stale:
        try:
            _ws_clients.discard(ws)
            await ws.close()
        except Exception:
            pass


@function_tool
def generate_subject(body: str) -> str:
    """Generate a simple subject line from the first line of the body."""
    if not body:
        return "Quick introduction"
    return body.splitlines()[0][:60]  # first line only, max 60 chars


@function_tool
def send_html_email(subject: str, html_body: str, to_email: Optional[str] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Send out an email with the given subject and HTML body via SendGrid.

    Accepts dynamic recipient via to_email and optional SMTP-style headers
    (e.g., In-Reply-To, References) to support threading.
    Returns response headers so caller can capture provider Message-ID.
    """
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get("SENDGRID_API_KEY"))
    # Sender email from environment variable (set by user in frontend)
    default_from = os.environ.get("DEFAULT_FROM_EMAIL")
    if not default_from:
        raise ValueError("No sender email configured. Please set your From Email in Settings.")
    default_to = os.environ.get("DEFAULT_TO_EMAIL")
    # Require explicit destination (either argument or env var)
    if not (to_email or default_to):
        raise ValueError("No destination email provided. Pass to_email or set DEFAULT_TO_EMAIL.")

    from_email = Email(default_from)
    to_email_obj = To(to_email or default_to)
    content = Content("text/html", html_body)
    mail_obj = Mail(from_email, to_email_obj, subject, content)

    # Add optional headers for email threading
    if headers:
        for k, v in headers.items():
            if v:
                try:
                    mail_obj.add_header(Header(k, v))
                except Exception:
                    try:
                        mail_obj.headers = {**getattr(mail_obj, "headers", {}), k: v}
                    except Exception:
                        pass

    response = sg.client.mail.send.post(request_body=mail_obj.get())
    resp_headers = getattr(response, "headers", {}) or {}
    message_id = resp_headers.get("X-Message-Id") or resp_headers.get("Message-Id")
    return {"status": "success", "subject": subject, "message_id": message_id, "provider_headers": dict(resp_headers)}


@function_tool
@app.post("/incoming-reply")
async def receive_incoming_reply(request: Request):
    """
    Webhook endpoint: gets reply emails, runs the reply pipeline,
    and sends the managed reply back via SendGrid.
    """
    data = await request.json()

    # Normalize payload keys to lower-case for robustness (accepts From/Subject/Text/Body variants)
    if isinstance(data, dict):
        data_lower = { (k.lower() if isinstance(k, str) else k): v for k, v in data.items() }
    else:
        data_lower = {}

    email_from = data_lower.get("from", "unknown@example.com")
    subject = data_lower.get("subject", "(no subject)")
    body = data_lower.get("text", data_lower.get("body", ""))
    inbound_message_id = data_lower.get("message_id")
    # Attempt to read headers if provided; normalize header keys
    headers_obj = data_lower.get("headers")
    if isinstance(headers_obj, dict) and not inbound_message_id:
        h_lower = { (k.lower() if isinstance(k, str) else k): v for k, v in headers_obj.items() }
        inbound_message_id = h_lower.get("message-id") or h_lower.get("message_id")
    # Optional References header (may be a string of angle-bracketed ids)
    references_raw = None
    if isinstance(headers_obj, dict):
        h_lower = { (k.lower() if isinstance(k, str) else k): v for k, v in headers_obj.items() }
        references_raw = h_lower.get("references")

    # Broadcast: Reply received
    await _broadcast({
        "type": "reply_received",
        "from": email_from,
        "subject": subject,
        "message_id": inbound_message_id
    })

    # Persist inbound for threading
    try:
        if inbound_message_id:
            record_inbound_message(email_from, inbound_message_id, references_raw)
    except Exception:
        pass

    # Import here to avoid circular import at module load time
    from .workflow import run_reply_workflow

    # Broadcast: Reply pipeline started
    await _broadcast({
        "type": "reply_pipeline_started",
        "from": email_from,
        "subject": subject
    })

    try:
        # Run the reply pipeline
        result = await run_reply_workflow(email_from, subject, body, inbound_message_id=inbound_message_id, references=references_raw)

        # The Reply Email Manager already sent the formatted HTML.
        # Avoid sending a second, poorly formatted email from here.
        managed_reply = result.get("final_output", "Thanks for your reply!")
        email_send_status = "sent_by_manager"

        # Broadcast: Reply sent successfully
        await _broadcast({
            "type": "reply_sent",
            "from": email_from,
            "to": email_from,
            "status": "success"
        })

        return {
            **result,
            "reply_sent": managed_reply,
            "status": "processed (email sent by manager)",
            "email_send_status": email_send_status
        }
    except Exception as e:
        # Broadcast: Reply pipeline error
        await _broadcast({
            "type": "reply_error",
            "from": email_from,
            "error": str(e)
        })
        raise


# --- Minimal API for UI ---

@app.post("/api/keys")
async def set_keys(request: Request):
    """Accept OpenAI and SendGrid API keys and sender email, set for this process (no persistence)."""
    try:
        data = await request.json()
    except Exception:
        data = {}
    openai_key = (data or {}).get("openai_api_key")
    sendgrid_key = (data or {}).get("sendgrid_api_key")
    from_email = (data or {}).get("from_email")
    if isinstance(openai_key, str) and openai_key.strip():
        os.environ["OPENAI_API_KEY"] = openai_key.strip()
    if isinstance(sendgrid_key, str) and sendgrid_key.strip():
        os.environ["SENDGRID_API_KEY"] = sendgrid_key.strip()
    if isinstance(from_email, str) and from_email.strip():
        os.environ["DEFAULT_FROM_EMAIL"] = from_email.strip()
    return {"status": "ok"}


@app.post("/api/cold/send")
async def api_cold_send(request: Request):
    """Trigger a single cold email send."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    email = (payload or {}).get("email")
    name = (payload or {}).get("name")
    pitch = (payload or {}).get("pitch") or (
        "I'm reaching out to connect and explore potential opportunities for collaboration."
    )
    if not email:
        return {"status": "error", "error": "missing_email"}
    await _broadcast({"type": "cold_send_started", "email": email})
    try:
        result = await run_cold_workflow(pitch, recipient_email=email, recipient_name=name)
        await _broadcast({"type": "cold_send_completed", "email": email})
        return {"status": "ok", "result": {"email": email, "final_output": result.get("final_output")}}
    except Exception as e:
        await _broadcast({"type": "cold_send_error", "email": email, "error": str(e)})
        return {"status": "error", "error": str(e)}


@app.post("/api/cold/upload")
async def api_cold_upload(file: UploadFile = File(...)):
    """Upload a CSV and trigger bulk cold sends."""
    if not file:
        return {"status": "error", "error": "missing_file"}
    # Parse CSV in-memory
    try:
        content = await file.read()
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(text.splitlines())
        recipients: List[Dict[str, Optional[str]]] = []
        email_keys = {"email", "recipient_email", "to", "to_email"}
        name_keys = {"name", "recipient_name", "first_name", "full_name"}
        for row in reader:
            if not isinstance(row, dict):
                continue
            norm = { (k.lower() if isinstance(k, str) else k): v for k, v in row.items() }
            email = None
            name = None
            for k in email_keys:
                if k in norm and norm[k]:
                    email = str(norm[k]).strip()
                    break
            for k in name_keys:
                if k in norm and norm[k]:
                    name = str(norm[k]).strip()
                    break
            if email:
                recipients.append({"email": email, "name": name})
    except Exception as e:
        return {"status": "error", "error": f"csv_parse_error: {e}"}

    await _broadcast({"type": "bulk_started", "count": len(recipients)})
    # Run sends concurrently with a cap
    sem = asyncio.Semaphore(3)
    results: List[Dict[str, Any]] = []

    async def _one(rec: Dict[str, Optional[str]]):
        email = rec.get("email")
        name = rec.get("name")
        if not email:
            return
        await _broadcast({"type": "cold_send_started", "email": email})
        async with sem:
            try:
                r = await run_cold_workflow(
                    "I'm reaching out to connect and explore potential opportunities for collaboration.",
                    recipient_email=email,
                    recipient_name=name,
                )
                results.append({"email": email, "final_output": r.get("final_output")})
                await _broadcast({"type": "cold_send_completed", "email": email})
            except Exception as e:
                results.append({"email": email, "error": str(e)})
                await _broadcast({"type": "cold_send_error", "email": email, "error": str(e)})

    await asyncio.gather(*[_one(r) for r in recipients])
    await _broadcast({"type": "bulk_completed", "count": len(results)})
    return {"status": "ok", "count": len(results)}


@app.websocket("/ws/progress")
async def ws_progress(ws: WebSocket):
    await ws.accept()
    _ws_clients.add(ws)
    try:
        while True:
            # Keep the connection open; we don't expect inbound messages
            await ws.receive_text()
    except WebSocketDisconnect:
        _ws_clients.discard(ws)
    except Exception:
        _ws_clients.discard(ws)


# Serve frontend if built under ./frontend/dist
_frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
_frontend_dist = os.path.abspath(_frontend_dist)
if os.path.isdir(_frontend_dist):
    # Serve built frontend at root so /assets paths resolve; API routes start with /api and are unaffected
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
else:
    @app.get("/", response_class=HTMLResponse)
    async def index():
        # Minimal no-build React-like UI via vanilla JS
        return HTMLResponse(
            """
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Cold Email Agent</title>
  <style>
    body { margin: 0; font-family: Arial, sans-serif; color: #0f172a; }
    .app { display: flex; height: 100vh; }
    .sidebar { width: 300px; background: #0b1220; color: #e2e8f0; padding: 16px; box-sizing: border-box; }
    .sidebar h2 { margin-top: 0; font-size: 18px; }
    .field { margin-bottom: 12px; }
    .field label { display: block; font-size: 12px; margin-bottom: 4px; color: #a3aed0; }
    .field input { width: 100%; padding: 8px; border: 1px solid #334155; border-radius: 6px; background: #0f172a; color: #e2e8f0; }
    .button { display: inline-block; background: #2563eb; color: white; border: none; border-radius: 6px; padding: 10px 12px; cursor: pointer; }
    .button.secondary { background: #1f2937; }
    .content { flex: 1; background: #f8fafc; padding: 24px; box-sizing: border-box; }
    .card { max-width: 720px; background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px; }
    .row { display: flex; gap: 12px; align-items: center; }
    .row input[type=\"email\"] { flex: 1; padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; }
    .attach { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; color: #334155; border: 1px dashed #94a3b8; padding: 8px 12px; border-radius: 8px; }
    .log { margin-top: 16px; max-height: 240px; overflow: auto; background: #0f172a; color: #e2e8f0; padding: 12px; border-radius: 8px; font-size: 12px; }
  </style>
  <script>
    let ws;
    function log(msg) {
      const el = document.getElementById('log');
      const time = new Date().toLocaleTimeString();
      el.textContent += `[${time}] ${msg}\n`;
      el.scrollTop = el.scrollHeight;
    }
    function saveKeys() {
      const openai = document.getElementById('openai').value.trim();
      const sendgrid = document.getElementById('sendgrid').value.trim();
      const fromEmail = document.getElementById('fromEmail').value.trim();
      fetch('/api/keys', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ openai_api_key: openai, sendgrid_api_key: sendgrid, from_email: fromEmail }) })
        .then(() => log('API keys saved for this session'))
        .catch(e => log('Error saving keys: ' + e));
    }
    function sendSingle() {
      const email = document.getElementById('email').value.trim();
      const name = document.getElementById('name').value.trim();
      if (!email) { log('Please enter an email'); return; }
      fetch('/api/cold/send', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, name }) })
        .then(r => r.json()).then(j => log('Send result: ' + JSON.stringify(j)))
        .catch(e => log('Error: ' + e));
    }
    function uploadCsv(input) {
      const file = input.files[0];
      if (!file) return;
      const fd = new FormData();
      fd.append('file', file);
      fetch('/api/cold/upload', { method: 'POST', body: fd })
        .then(r => r.json()).then(j => log('Bulk upload: ' + JSON.stringify(j)))
        .catch(e => log('Upload error: ' + e));
    }
    function connectWs() {
      try {
        ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/progress');
        ws.onopen = () => log('WebSocket connected');
        ws.onmessage = (ev) => {
          try { const data = JSON.parse(ev.data); log('Event: ' + JSON.stringify(data)); }
          catch { log('WS message: ' + ev.data); }
        };
        ws.onclose = () => log('WebSocket closed');
      } catch (e) { log('WS error: ' + e); }
    }
    window.addEventListener('DOMContentLoaded', connectWs);
  </script>
</head>
<body>
  <div class=\"app\">
    <aside class=\"sidebar\">
      <h2>Settings</h2>
      <div class=\"field\">
        <label for=\"openai\">OpenAI API Key</label>
        <input id=\"openai\" type=\"password\" placeholder=\"sk-...\" />
      </div>
      <div class=\"field\">
        <label for=\"sendgrid\">SendGrid API Key</label>
        <input id=\"sendgrid\" type=\"password\" placeholder=\"SG....\" />
      </div>
      <div class=\"field\">
        <label for=\"fromEmail\">From Email (Sender)</label>
        <input id=\"fromEmail\" type=\"email\" placeholder=\"you@example.com\" />
        <small style=\"color: #94a3b8; margin-top: 4px; display: block;\">Use email verified in SendGrid. <a href=\"https://app.sendgrid.com/settings/sender_auth\" target=\"_blank\" style=\"color: #60a5fa;\">Setup here</a></small>
      </div>
      <button class=\"button\" onclick=\"saveKeys()\">Save Keys</button>
    </aside>
    <main class=\"content\">
      <div class=\"card\">
        <h3>Cold Outreach</h3>
        <div class=\"row\" style=\"margin-bottom:12px;\">
          <input id=\"email\" type=\"email\" placeholder=\"Enter recipient email\" />
          <input id=\"name\" type=\"text\" placeholder=\"Recipient name (optional)\" style=\"flex:0.6; padding:10px; border:1px solid #cbd5e1; border-radius:8px;\" />
          <button class=\"button\" onclick=\"sendSingle()\">Send</button>
        </div>
        <div class=\"row\">
          <label class=\"attach\" for=\"csv\">📎 Attach CSV</label>
          <input id=\"csv\" type=\"file\" accept=\".csv\" style=\"display:none\" onchange=\"uploadCsv(this)\" />
          <button class=\"button secondary\" onclick=\"document.getElementById('csv').click()\">Choose CSV</button>
        </div>
        <div class=\"log\" id=\"log\" aria-live=\"polite\"></div>
      </div>
    </main>
  </div>
</body>
</html>
            """
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

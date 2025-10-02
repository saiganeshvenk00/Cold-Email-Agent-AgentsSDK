import os
from typing import Dict, Optional
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content, Header
from agent_sdk import function_tool
from fastapi import FastAPI, Request
import uvicorn
from dotenv import load_dotenv
from thread_store import record_inbound_message

# Load environment variables for local/dev runs
load_dotenv()

# Create a FastAPI application instance
app = FastAPI()


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
    # Sender is fixed as per requirement
    default_from = "saiganeshv00@gmail.com"
    default_to = os.environ.get("DEFAULT_TO_EMAIL", "saiganeshvenk00@gmail.com")

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

    # Persist inbound for threading
    try:
        if inbound_message_id:
            record_inbound_message(email_from, inbound_message_id, references_raw)
    except Exception:
        pass

    # Import here to avoid circular import at module load time
    from .workflow import run_reply_workflow

    # Run the reply pipeline
    result = await run_reply_workflow(email_from, subject, body, inbound_message_id=inbound_message_id, references=references_raw)

    # The Reply Email Manager already sent the formatted HTML.
    # Avoid sending a second, poorly formatted email from here.
    managed_reply = result.get("final_output", "Thanks for your reply!")
    email_send_status = "sent_by_manager"

    return {
        **result,
        "reply_sent": managed_reply,
        "status": "processed (email sent by manager)",
        "email_send_status": email_send_status
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

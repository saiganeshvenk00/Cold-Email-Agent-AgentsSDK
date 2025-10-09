import os
import re
from typing import Dict, Optional
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content, Header
from agent_sdk import function_tool


@function_tool
def generate_subject(body: str) -> str:
    """Generate a simple subject line from the first part of the body."""
    if not body:
        return "Quick introduction"
    return body.splitlines()[0][:60]  # just take the first line, max 60 chars


@function_tool
def send_html_email(subject: str, html_body: str, to_email: Optional[str] = None, headers: Optional[Dict[str, str]] = None) -> dict:
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
                    # Fallback to setting raw headers dict if helper fails
                    try:
                        mail_obj.headers = {**getattr(mail_obj, "headers", {}), k: v}
                    except Exception:
                        pass

    response = sg.client.mail.send.post(request_body=mail_obj.get())
    # Common SendGrid header key is 'X-Message-Id'
    resp_headers = getattr(response, "headers", {}) or {}
    message_id = resp_headers.get("X-Message-Id") or resp_headers.get("Message-Id")
    return {"status": "success", "subject": subject, "message_id": message_id, "provider_headers": dict(resp_headers)}


@function_tool
def derive_recipient_name(email: str = "", fallback: str = "") -> str:
    """Derive a likely recipient full name from an email address.

    - If a fallback name is provided, return it.
    - Otherwise, parse the local part of the email (before @) using simple heuristics:
      - Split on dots/underscores/hyphens
      - Ignore role-like tokens (info, hello, sales, contact, support)
      - Capitalize first two tokens -> "john.doe" -> "John Doe"
    Returns an empty string if no good candidate found.
    """
    if fallback and fallback.strip():
        return fallback.strip()
    if not email or "@" not in email:
        return ""
    local = email.split("@", 1)[0]
    role_tokens = {"info", "hello", "sales", "contact", "support", "team", "noreply", "no-reply"}
    raw_parts = [p for p in re.split(r"[._-]+", local) if p]
    parts = []
    for p in raw_parts:
        p_clean = re.sub(r"\d+", "", p)
        if p_clean and p_clean.isalpha() and p_clean.lower() not in role_tokens:
            parts.append(p_clean)
    if not parts:
        return ""
    parts = parts[:2]
    return " ".join(w.capitalize() for w in parts)

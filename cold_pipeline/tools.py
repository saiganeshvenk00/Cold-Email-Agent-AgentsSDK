import os
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from agent_sdk import function_tool
import re


@function_tool
def generate_subject(body: str) -> str:
    """Generate a simple subject line from the first part of the body."""
    if not body:
        return "Quick introduction"
    return body.splitlines()[0][:60]  # just take the first line, max 60 chars


@function_tool
def send_html_email(subject: str, html_body: str) -> dict:
    """Send out an email with the given subject and HTML body via SendGrid."""
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get("SENDGRID_API_KEY"))
    from_email = Email("saiganeshv00@gmail.com")   # hardcoded like Ed’s notebook
    to_email = To("saiganeshvenk00@gmail.com")        # hardcoded like Ed’s notebook
    content = Content("text/html", html_body)
    mail = Mail(from_email, to_email, subject, content).get()
    sg.client.mail.send.post(request_body=mail)
    return {"status": "success", "subject": subject}


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

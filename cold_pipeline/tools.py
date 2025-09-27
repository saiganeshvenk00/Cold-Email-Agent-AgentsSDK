import os
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from agent_sdk import function_tool


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

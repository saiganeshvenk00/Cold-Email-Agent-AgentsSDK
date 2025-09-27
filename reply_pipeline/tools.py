import os
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from typing import Dict
from agent_sdk import function_tool

@function_tool
def send_html_email(subject: str, html_body: str, to_email: str = "ed.donner@gmail.com") -> Dict[str, str]:
    """
    Send a reply email with the given subject and HTML body via SendGrid.
    """
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get("SENDGRID_API_KEY"))
    from_email = Email("ed@edwarddonner.com")   # change to verified sender
    to_email = To(to_email)                     # dynamic recipient
    content = Content("text/html", html_body)
    mail = Mail(from_email, to_email, subject, content).get()
    sg.client.mail.send.post(request_body=mail)
    return {"status": "success", "subject": subject, "to": str(to_email)}

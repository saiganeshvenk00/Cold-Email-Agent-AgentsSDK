import os
from typing import Dict
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from agent_sdk import function_tool


@function_tool
def generate_subject(body: str) -> str:
    """Generate a simple subject line from the first line of the body."""
    if not body:
        return "Quick introduction"
    return body.splitlines()[0][:60]  # first line only, max 60 chars


@function_tool
def send_html_email(subject: str, html_body: str) -> Dict[str, str]:
    """Send out an email with the given subject and HTML body via SendGrid."""
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get("SENDGRID_API_KEY"))
    from_email = Email("saiganeshv00@gmail.com")   # hardcoded like Ed’s notebook
    to_email = To("saiganeshvenk00@gmail.com")     # hardcoded for demo
    content = Content("text/html", html_body)
    mail = Mail(from_email, to_email, subject, content).get()
    sg.client.mail.send.post(request_body=mail)
    return {"status": "success", "subject": subject}


import os
from fastapi import FastAPI, Request
from agent_sdk import function_tool
import uvicorn

# Create a FastAPI application instance
app = FastAPI()




@function_tool
@app.post("/incoming-reply")
async def receive_incoming_reply(request: Request):
    """
    Webhook endpoint: gets reply emails and triggers the reply pipeline.
    """
    data = await request.json()

    email_from = data.get("from", "unknown@example.com")
    subject = data.get("subject", "(no subject)")
    body = data.get("text", data.get("body", ""))

    # Import here to avoid circular import at module load time
    from .workflow import run_reply_workflow

    # Run the reply pipeline
    result = await run_reply_workflow(email_from, subject, body)

    return result

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
    Real webhook: SendGrid (or another email provider) posts replies here.
    Returns sender, subject, and body so the reply pipeline can use them.
    """
    # Parse JSON payload from SendGrid (Inbound Parse or custom forwarder)
    data = await request.json()

    # Extract useful fields with defaults
    email_from = data.get("from", "unknown@example.com")
    subject = data.get("subject", "(no subject)")
    body = data.get("text", data.get("body", ""))  # "text" is common in SendGrid payloads

    # Return a dict, which the agent pipeline can process
    return {
        "from": email_from,
        "subject": subject,
        "body": body,
        "status": "received"
    }


if __name__ == "__main__":
    # Launch FastAPI server on port 8000 when run directly
    uvicorn.run(app, host="0.0.0.0", port=8000)

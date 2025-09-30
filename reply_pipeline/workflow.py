import os
from typing import Dict
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from agent_sdk import function_tool
from fastapi import FastAPI, Request

# Create FastAPI app
app = FastAPI()

@function_tool
def generate_subject(body: str) -> str:
    if not body:
        return "Quick introduction"
    return body.splitlines()[0][:60]

@function_tool
def send_html_email(subject: str, html_body: str) -> Dict[str, str]:
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get("SENDGRID_API_KEY"))
    from_email = Email("saiganeshv00@gmail.com")
    to_email = To("saiganeshvenk00@gmail.com")
    content = Content("text/html", html_body)
    mail = Mail(from_email, to_email, subject, content).get()
    sg.client.mail.send.post(request_body=mail)
    return {"status": "success", "subject": subject}

@app.post("/incoming-reply")
async def receive_incoming_reply(request: Request):
    data = await request.json()
    email_from = data.get("from", "unknown@example.com")
    subject = data.get("subject", "(no subject)")
    body = data.get("text", data.get("body", ""))
    return {"from": email_from, "subject": subject, "body": body, "status": "received"}

import os
from typing import Dict
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from agent_sdk import function_tool
from fastapi import FastAPI, Request
import uvicorn
from dotenv import load_dotenv

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
def send_html_email(subject: str, html_body: str) -> Dict[str, str]:
    """Send out an email with the given subject and HTML body via SendGrid."""
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get("SENDGRID_API_KEY"))
    from_email = Email("saiganeshv00@gmail.com")   # hardcoded like Ed’s notebook
    to_email = To("saiganeshvenk00@gmail.com")     # hardcoded for demo
    content = Content("text/html", html_body)
    mail = Mail(from_email, to_email, subject, content).get()
    sg.client.mail.send.post(request_body=mail)
    return {"status": "success", "subject": subject}


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

    # Import here to avoid circular import at module load time
    from .workflow import run_reply_workflow

    # Run the reply pipeline
    result = await run_reply_workflow(email_from, subject, body)

    # Extract managed reply (or fallback if missing)
    managed_reply = result.get("final_output", "Thanks for your reply!")

    # Send the email out (do not fail the webhook response on send issues)
    email_send_status = "sent"
    try:
        send_html_email(f"Re: {subject}", f"<p>{managed_reply}</p>")
    except Exception as e:
        email_send_status = f"failed: {str(e)}"

    return {
        **result,
        "reply_sent": managed_reply,
        "status": "processed and replied",
        "email_send_status": email_send_status
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

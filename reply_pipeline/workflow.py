from .agents import reply_agent, reply_email_manager
from .sendgrid_utils import send_reply_email
from agents import Runner  # from the Agents SDK

async def run_reply_workflow(email_from: str, email_subject: str, email_body: str) -> dict:
    """
    Orchestrates the reply pipeline:
    1. Draft reply using Reply Agent
    2. Polish/manage reply using Reply Email Manager
    3. Send formatted reply via SendGrid
    """
    # Step A: Draft reply
    reply_draft = await Runner.run(reply_agent, email_body)

    # Step B: Manage/format draft with Reply Email Manager
    managed_reply = await Runner.run(reply_email_manager, reply_draft.final_output)

    # Step C: Send via SendGrid
    status_code = send_reply_email(
        to_email=email_from,
        subject=f"Re: {email_subject}",
        body_text=managed_reply.final_output
    )

    return {
        "to": email_from,
        "original_subject": email_subject,
        "reply_draft": reply_draft.final_output,
        "managed_reply": managed_reply.final_output,
        "status": f"Sent via SendGrid (status {status_code})"
    }

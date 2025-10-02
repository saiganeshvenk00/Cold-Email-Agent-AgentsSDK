from typing import Optional, Dict, Any
from agent_sdk import Runner
from .agents import reply_email_manager, reply_agent

async def run_reply_workflow(email_from: str, subject: str, body: str, inbound_message_id: Optional[str] = None, references: Optional[str] = None) -> dict:
    """
    Entry point for the reply pipeline.
    Forwards the incoming email body to the Reply Email Manager.
    Returns the pipeline result along with the received fields.
    """
    # First, draft a reply using the Reply Agent
    reply_draft_res = await Runner.run(reply_agent, body)
    reply_draft = getattr(reply_draft_res, "final_output", body)

    # Forward draft to the Reply Email Manager for HTML formatting and sending
    input_text = f"To: {email_from}\n\n{reply_draft}" if email_from else reply_draft
    context: Dict[str, Any] = {
        "to_email": email_from,
        "inbound_message_id": inbound_message_id,
        "references": references,
    }
    result = await Runner.run(reply_email_manager, input_text, context=context)

    return {
        "from": email_from,
        "subject": subject,
        "body": body,
        "final_output": getattr(result, "final_output", None),
        "raw_result": result,
        "draft": reply_draft,
    }

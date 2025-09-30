from agent_sdk import Runner
from .agents import reply_email_manager

async def run_reply_workflow(email_from: str, subject: str, body: str) -> dict:
    """
    Entry point for the reply pipeline. It forwards the incoming email body
    (optionally prefixed with a To: header) to the Reply Email Manager.
    Returns the pipeline result along with the received fields.
    """
    input_text = f"To: {email_from}\n\n{body}" if email_from else body
    result = await Runner.run(reply_email_manager, input_text)
    return {
        "from": email_from,
        "subject": subject,
        "body": body,
        "final_output": getattr(result, "final_output", None),
        "raw_result": result,
    }

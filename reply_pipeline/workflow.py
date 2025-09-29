import asyncio
from agent_sdk import Runner
from .agents import reply_agent, reply_email_manager
from .tools import receive_incoming_reply

async def run_reply_workflow(incoming_text: str, to_email: str) -> dict:
    """
    Full reply pipeline:
    1. Reply Agent drafts a response.
    2. Reply Email Manager formats and sends it via SendGrid.
    """

    # Step 0: Ingest incoming reply via tool (simulated webhook)
    ingested = receive_incoming_reply(
        email_from="unknown@example.com",
        subject="Incoming reply",
        body=incoming_text,
    )
    normalized_text = ingested.get("body", incoming_text)

    # Step A: Generate draft reply
    draft_reply = await Runner.run(reply_agent, normalized_text)

    # Step B: Email Manager finalizes and sends
    managed_reply = await Runner.run(
        reply_email_manager,
        f"To: {to_email}\n\n{draft_reply.final_output}"
    )

    return {
        "draft_reply": draft_reply.final_output,
        "managed_reply": managed_reply.final_output
    }

# For quick testing
if __name__ == "__main__":
    async def main():
        incoming = "Thanks for your email. Can you share more about your experience?"
        output = await run_reply_workflow(incoming, "recruiter@example.com")
        print("Reply Workflow result:\n", output)

    asyncio.run(main())

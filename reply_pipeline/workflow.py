import asyncio
from agent_sdk import Runner
from .agents import reply_agent, reply_email_manager

async def run_reply_workflow(incoming_text: str, to_email: str) -> dict:
    """
    Full reply pipeline:
    1. Reply Agent drafts a response.
    2. Reply Email Manager formats and sends it via SendGrid.
    """

    # Step A: Generate draft reply
    draft_reply = await Runner.run(reply_agent, incoming_text)

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

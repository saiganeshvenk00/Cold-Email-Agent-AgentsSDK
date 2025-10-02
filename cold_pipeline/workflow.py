import asyncio
from agent_sdk import Runner
from .agents import sales_manager

async def run_cold_workflow(product_pitch: str, recipient_email: str | None = None, recipient_name: str | None = None) -> dict:
    """
    Entry point for running the cold email workflow.
    This kicks off the Sales Manager agent, which:
      1. Collects drafts from Sales Agents
      2. Passes them to the Sales Picker
      3. Forwards the winning draft to the Email Manager
      4. Email Manager generates subject, formats HTML, and sends via SendGrid
    """

    context = {"recipient_email": recipient_email, "recipient_name": recipient_name}
    result = await Runner.run(sales_manager, product_pitch, context=context)

    return {
        "final_output": result.final_output,
        "raw_result": result  # in case you want to inspect tool calls, steps, etc.
    }

# If running this file directly for a quick test
if __name__ == "__main__":
    async def main():
        pitch = "I'm a Solutions Architect with 3 years experience in AI infrastructure and presales, now exploring roles at the intersection of AI and product."
        output = await run_cold_workflow(pitch)
        print("Workflow result:\n", output)

    asyncio.run(main())
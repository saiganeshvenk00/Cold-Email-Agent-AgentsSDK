import asyncio
from dotenv import load_dotenv
from cold_pipeline import run_cold_workflow
from reply_pipeline import run_reply_workflow

async def main():
    # Load environment variables from .env for local testing
    load_dotenv()
    # --- Example: Cold pipeline ---
    cold_pitch = (
        "I'm a Solutions Architect with 3 years of experience in AI infrastructure and presales, "
        "and I’m reaching out to explore opportunities at your company."
    )
    cold_result = await run_cold_workflow(cold_pitch)
    print("\n=== Cold Pipeline Result ===")
    print(cold_result)

    # --- Example: Reply pipeline (guarded demo) ---
    # Set RUN_REPLY_DEMO=1 to run this example; otherwise it will be skipped.
    import os
    if os.environ.get("RUN_REPLY_DEMO") == "1":
        incoming_email = "Thanks for your email, could you share more about your background?"
        incoming_email_from = "recruiter@example.com"
        subject = "Re: Your email"
        body = incoming_email
        reply_result = await run_reply_workflow(incoming_email_from, subject, body)
        print("\n=== Reply Pipeline Result ===")
        print(reply_result)

if __name__ == "__main__":
    asyncio.run(main())

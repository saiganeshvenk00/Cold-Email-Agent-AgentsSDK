import asyncio
from cold_pipeline import run_cold_workflow
from reply_pipeline import run_reply_workflow

async def main():
    # --- Example: Cold pipeline ---
    cold_pitch = (
        "I'm a Solutions Architect with 3 years of experience in AI infrastructure and presales, "
        "and I’m reaching out to explore opportunities at your company."
    )
    cold_result = await run_cold_workflow(cold_pitch)
    print("\n=== Cold Pipeline Result ===")
    print(cold_result)

    # --- Example: Reply pipeline ---
    incoming_email = "Thanks for your email, could you share more about your background?"
    reply_result = await run_reply_workflow(incoming_email, to_email="recruiter@example.com")
    print("\n=== Reply Pipeline Result ===")
    print(reply_result)

if __name__ == "__main__":
    asyncio.run(main())

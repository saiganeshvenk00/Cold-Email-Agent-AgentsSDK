import asyncio
import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from cold_pipeline import run_cold_workflow, run_cold_workflow_bulk
from reply_pipeline import run_reply_workflow

# FastAPI app for Vercel (exports `app` and `handler`)
app = FastAPI()
handler = app  # Some platforms look specifically for `handler`


class ColdRequest(BaseModel):
    product_pitch: str
    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None


class ColdBulkRequest(BaseModel):
    product_pitch: str
    recipients: Optional[List[Dict[str, Optional[str]]]] = None
    csv_path: Optional[str] = None
    concurrency: int = 3


class ReplyRequest(BaseModel):
    email_from: str
    subject: str
    body: str
    inbound_message_id: Optional[str] = None
    references: Optional[str] = None


def _strip_raw_result(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _strip_raw_result(v) for k, v in data.items() if k != "raw_result"}
    if isinstance(data, list):
        return [_strip_raw_result(v) for v in data]
    return data


@app.get("/api/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/cold")
async def api_cold(payload: ColdRequest) -> Dict[str, Any]:
    try:
        result = await run_cold_workflow(
            payload.product_pitch,
            recipient_email=payload.recipient_email,
            recipient_name=payload.recipient_name,
        )
        return _strip_raw_result(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cold/bulk")
async def api_cold_bulk(payload: ColdBulkRequest) -> Dict[str, Any]:
    try:
        recipients_or_path: Any = payload.csv_path if payload.csv_path else (payload.recipients or [])
        result_list = await run_cold_workflow_bulk(
            payload.product_pitch,
            recipients_or_path,
            concurrency=max(1, int(payload.concurrency)),
        )
        return {"results": _strip_raw_result(result_list)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reply")
async def api_reply(payload: ReplyRequest) -> Dict[str, Any]:
    try:
        result = await run_reply_workflow(
            payload.email_from,
            payload.subject,
            payload.body,
            inbound_message_id=payload.inbound_message_id,
            references=payload.references,
        )
        return _strip_raw_result(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def main():
    # Load environment variables from .env for local testing
    load_dotenv()
    # --- Example: Cold pipeline ---
    import os
    cold_pitch = (
        "I'm a Solutions Architect with 3 years of experience in AI infrastructure and presales, "
        "and I’m reaching out to explore opportunities at your company."
    )
    csv_path = os.environ.get("COLD_RECIPIENTS_CSV")
    if csv_path:
        bulk_results = await run_cold_workflow_bulk(cold_pitch, csv_path, concurrency=3)
        print("\n=== Cold Pipeline Bulk Result ===")
        print({"count": len(bulk_results)})
    else:
        recipient_email = os.environ.get("COLD_RECIPIENT_EMAIL")
        if not recipient_email:
            try:
                recipient_email = input("Enter recipient email (leave blank to provide CSV path): ").strip()
            except Exception:
                recipient_email = None
        if not recipient_email:
            try:
                csv_path = input("Enter path to CSV (leave blank to skip): ").strip()
            except Exception:
                csv_path = ""
            if csv_path:
                bulk_results = await run_cold_workflow_bulk(cold_pitch, csv_path, concurrency=3)
                print("\n=== Cold Pipeline Bulk Result ===")
                print({"count": len(bulk_results)})
            else:
                print("No recipient provided. Skipping cold pipeline.")
        else:
            recipient_name = os.environ.get("COLD_RECIPIENT_NAME")
            cold_result = await run_cold_workflow(cold_pitch, recipient_email=recipient_email, recipient_name=recipient_name)
            print("\n=== Cold Pipeline Result ===")
            print(cold_result)

    # --- Example: Reply pipeline (guarded demo) ---
    # Set RUN_REPLY_DEMO=1 to run this example; otherwise it will be skipped.
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

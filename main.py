import asyncio
import os
import csv
from typing import Optional, List, Dict, Any, Set
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from cold_pipeline import run_cold_workflow, run_cold_workflow_bulk
from reply_pipeline import run_reply_workflow
from thread_store import record_inbound_message

# Load environment variables
load_dotenv()

# FastAPI app for Vercel (exports `app` and `handler`)
app = FastAPI()
handler = app  # Some platforms look specifically for `handler`

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket clients registry
_ws_clients: Set[WebSocket] = set()

async def _broadcast(event: Dict[str, Any]) -> None:
    """Broadcast events to all connected WebSocket clients."""
    if not _ws_clients:
        return
    stale: List[WebSocket] = []
    for ws in list(_ws_clients):
        try:
            await ws.send_json(event)
        except Exception:
            stale.append(ws)
    for ws in stale:
        try:
            _ws_clients.discard(ws)
            await ws.close()
        except Exception:
            pass


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


# ===== WEBHOOK ENDPOINT FOR INCOMING REPLIES =====

@app.post("/incoming-reply")
async def receive_incoming_reply(request: Request):
    """
    Webhook endpoint: gets reply emails, runs the reply pipeline,
    and sends the managed reply back via SendGrid.
    """
    data = await request.json()

    # Normalize payload keys to lower-case for robustness
    if isinstance(data, dict):
        data_lower = { (k.lower() if isinstance(k, str) else k): v for k, v in data.items() }
    else:
        data_lower = {}

    email_from = data_lower.get("from", "unknown@example.com")
    subject = data_lower.get("subject", "(no subject)")
    body = data_lower.get("text", data_lower.get("body", ""))
    inbound_message_id = data_lower.get("message_id")
    
    # Attempt to read headers if provided
    headers_obj = data_lower.get("headers")
    if isinstance(headers_obj, dict) and not inbound_message_id:
        h_lower = { (k.lower() if isinstance(k, str) else k): v for k, v in headers_obj.items() }
        inbound_message_id = h_lower.get("message-id") or h_lower.get("message_id")
    
    # Optional References header
    references_raw = None
    if isinstance(headers_obj, dict):
        h_lower = { (k.lower() if isinstance(k, str) else k): v for k, v in headers_obj.items() }
        references_raw = h_lower.get("references")

    # Broadcast: Reply received
    await _broadcast({
        "type": "reply_received",
        "from": email_from,
        "subject": subject,
        "message_id": inbound_message_id
    })

    # Persist inbound for threading
    try:
        if inbound_message_id:
            record_inbound_message(email_from, inbound_message_id, references_raw)
    except Exception:
        pass

    # Broadcast: Reply pipeline started
    await _broadcast({
        "type": "reply_pipeline_started",
        "from": email_from,
        "subject": subject
    })

    try:
        # Run the reply pipeline
        result = await run_reply_workflow(
            email_from, subject, body,
            inbound_message_id=inbound_message_id,
            references=references_raw
        )

        managed_reply = result.get("final_output", "Thanks for your reply!")

        # Broadcast: Reply sent successfully
        await _broadcast({
            "type": "reply_sent",
            "from": email_from,
            "to": email_from,
            "status": "success"
        })

        return {
            **result,
            "reply_sent": managed_reply,
            "status": "processed (email sent by manager)",
            "email_send_status": "sent_by_manager"
        }
    except Exception as e:
        # Broadcast: Reply pipeline error
        await _broadcast({
            "type": "reply_error",
            "from": email_from,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))


# ===== UI API ENDPOINTS =====

@app.post("/api/keys")
async def set_keys(request: Request):
    """Accept OpenAI and SendGrid API keys and sender email."""
    try:
        data = await request.json()
    except Exception:
        data = {}
    
    openai_key = (data or {}).get("openai_api_key")
    sendgrid_key = (data or {}).get("sendgrid_api_key")
    from_email = (data or {}).get("from_email")
    
    if isinstance(openai_key, str) and openai_key.strip():
        os.environ["OPENAI_API_KEY"] = openai_key.strip()
    if isinstance(sendgrid_key, str) and sendgrid_key.strip():
        os.environ["SENDGRID_API_KEY"] = sendgrid_key.strip()
    if isinstance(from_email, str) and from_email.strip():
        os.environ["DEFAULT_FROM_EMAIL"] = from_email.strip()
    
    return {"status": "ok"}


@app.post("/api/cold/send")
async def api_cold_send(request: Request):
    """Trigger a single cold email send."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    
    email = (payload or {}).get("email")
    name = (payload or {}).get("name")
    pitch = (payload or {}).get("pitch") or (
        "I'm reaching out to connect and explore potential opportunities for collaboration."
    )
    
    if not email:
        return {"status": "error", "error": "missing_email"}
    
    await _broadcast({"type": "cold_send_started", "email": email})
    
    try:
        result = await run_cold_workflow(pitch, recipient_email=email, recipient_name=name)
        await _broadcast({"type": "cold_send_completed", "email": email})
        return {"status": "ok", "result": {"email": email, "final_output": result.get("final_output")}}
    except Exception as e:
        await _broadcast({"type": "cold_send_error", "email": email, "error": str(e)})
        return {"status": "error", "error": str(e)}


@app.post("/api/cold/upload")
async def api_cold_upload(file: UploadFile = File(...)):
    """Upload a CSV and trigger bulk cold sends."""
    if not file:
        return {"status": "error", "error": "missing_file"}
    
    # Parse CSV in-memory
    try:
        content = await file.read()
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(text.splitlines())
        recipients: List[Dict[str, Optional[str]]] = []
        email_keys = {"email", "recipient_email", "to", "to_email"}
        name_keys = {"name", "recipient_name", "first_name", "full_name"}
        
        for row in reader:
            if not isinstance(row, dict):
                continue
            norm = { (k.lower() if isinstance(k, str) else k): v for k, v in row.items() }
            email = None
            name = None
            for k in email_keys:
                if k in norm and norm[k]:
                    email = str(norm[k]).strip()
                    break
            for k in name_keys:
                if k in norm and norm[k]:
                    name = str(norm[k]).strip()
                    break
            if email:
                recipients.append({"email": email, "name": name})
    except Exception as e:
        return {"status": "error", "error": f"csv_parse_error: {e}"}

    await _broadcast({"type": "bulk_started", "count": len(recipients)})
    
    # Run sends concurrently with a cap
    sem = asyncio.Semaphore(3)
    results: List[Dict[str, Any]] = []

    async def _one(rec: Dict[str, Optional[str]]):
        email = rec.get("email")
        name = rec.get("name")
        if not email:
            return
        await _broadcast({"type": "cold_send_started", "email": email})
        async with sem:
            try:
                r = await run_cold_workflow(
                    "I'm reaching out to connect and explore potential opportunities for collaboration.",
                    recipient_email=email,
                    recipient_name=name,
                )
                results.append({"email": email, "final_output": r.get("final_output")})
                await _broadcast({"type": "cold_send_completed", "email": email})
            except Exception as e:
                results.append({"email": email, "error": str(e)})
                await _broadcast({"type": "cold_send_error", "email": email, "error": str(e)})

    await asyncio.gather(*[_one(r) for r in recipients])
    await _broadcast({"type": "bulk_completed", "count": len(results)})
    return {"status": "ok", "count": len(results)}


@app.websocket("/ws/progress")
async def ws_progress(ws: WebSocket):
    """WebSocket endpoint for real-time progress updates."""
    await ws.accept()
    _ws_clients.add(ws)
    try:
        while True:
            # Keep the connection open; we don't expect inbound messages
            await ws.receive_text()
    except WebSocketDisconnect:
        _ws_clients.discard(ws)
    except Exception:
        _ws_clients.discard(ws)


# ===== FRONTEND STATIC FILE SERVING =====

# Serve frontend if built under ./frontend/dist
_frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
_frontend_dist = os.path.abspath(_frontend_dist)
if os.path.isdir(_frontend_dist):
    # Serve built frontend at root so /assets paths resolve
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
else:
    @app.get("/")
    async def root():
        return {
            "message": "Cold Email Agent API",
            "status": "ok",
            "endpoints": {
                "health": "/api/health",
                "cold_email": "/api/cold",
                "bulk_cold": "/api/cold/bulk",
                "reply": "/api/reply",
                "webhook": "/incoming-reply",
                "websocket": "/ws/progress"
            },
            "note": "Frontend not built. Run 'cd frontend && npm run build' to enable UI."
        }


async def main():
    # Load environment variables from .env for local testing
    load_dotenv()
    # --- Example: Cold pipeline ---
    import os
    cold_pitch = os.environ.get("COLD_PITCH") or (
        "I'm reaching out to connect and explore potential opportunities for collaboration. "
        "I have experience in technology solutions and would love to discuss how we might work together."
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
    import sys
    import uvicorn
    
    # Check if we should run in CLI mode or server mode
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        # Run CLI mode
        asyncio.run(main())
    else:
        # Run server mode (default)
        port = int(os.environ.get("PORT", 8000))
        uvicorn.run(app, host="0.0.0.0", port=port)

import asyncio
import csv
from typing import List, Dict, Optional, Any
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


def load_recipients_from_csv(path: str) -> List[Dict[str, Optional[str]]]:
    """
    Load recipients from CSV. Tries common column names:
    - email keys: email, recipient_email, to, to_email
    - name keys: name, recipient_name, first_name, full_name
    """
    email_keys = {"email", "recipient_email", "to", "to_email"}
    name_keys = {"name", "recipient_name", "first_name", "full_name"}

    recipients: List[Dict[str, Optional[str]]] = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not isinstance(row, dict):
                continue
            # normalize keys
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
    return recipients


async def run_cold_workflow_bulk(
    product_pitch: str,
    recipients: List[Dict[str, Optional[str]]] | str,
    concurrency: int = 3,
) -> List[Dict[str, Any]]:
    """
    Send the cold email to many recipients.
    - recipients: either a CSV file path or a list of dicts with keys 'email' and optional 'name'
    - concurrency: limit of concurrent sends
    Returns a list of per-recipient results.
    """
    if isinstance(recipients, str):
        recipients_list = load_recipients_from_csv(recipients)
    else:
        recipients_list = [
            {
                "email": (r.get("email") or r.get("recipient_email") or r.get("to") or r.get("to_email")),
                "name": (r.get("name") or r.get("recipient_name") or r.get("first_name") or r.get("full_name")),
            }
            for r in recipients
        ]

    sem = asyncio.Semaphore(max(1, concurrency))
    results: List[Dict[str, Any]] = []

    async def _run_one(rec: Dict[str, Optional[str]]) -> None:
        email = (rec.get("email") or "").strip() if rec.get("email") else None
        name = (rec.get("name") or "").strip() if rec.get("name") else None
        if not email:
            results.append({"email": None, "name": name, "error": "missing_email"})
            return
        async with sem:
            try:
                context = {"recipient_email": email, "recipient_name": name}
                res = await Runner.run(sales_manager, product_pitch, context=context)
                results.append({
                    "email": email,
                    "name": name,
                    "final_output": getattr(res, "final_output", None),
                    "raw_result": res,
                })
            except Exception as e:
                results.append({"email": email, "name": name, "error": str(e)})

    await asyncio.gather(*[_run_one(r) for r in recipients_list])
    return results

# If running this file directly for a quick test
if __name__ == "__main__":
    async def main():
        pitch = "I'm a Solutions Architect with 3 years experience in AI infrastructure and presales, now exploring roles at the intersection of AI and product."
        output = await run_cold_workflow(pitch)
        print("Workflow result:\n", output)

    asyncio.run(main())
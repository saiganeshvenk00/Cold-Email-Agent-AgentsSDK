## COLD-EMAIL-AGENT-AGENTSSDK
Flattened project for a cold email agent system with a reply pipeline and webhook.

### Structure

```
COLD-EMAIL-AGENT-AGENTSSDK/
  cold_pipeline/
    original_notebook_code.py
  reply_pipeline/
    agents.py
    sendgrid_utils.py
    workflow.py
    webhook.py
  main.py
  requirements.txt
  README.md
  .env.example
  .env
```

### Setup

1. Copy `.env.example` to `.env` and fill values.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the webhook locally:
   ```bash
   uvicorn reply_pipeline.webhook:app --reload
   ```

### Test webhook

```bash
curl -X POST http://127.0.0.1:8000/webhook/reply \
  -H "Content-Type: application/json" \
  -H "x-verify-token: $WEBHOOK_VERIFY_TOKEN" \
  -d '{
    "from_email": "person@example.com",
    "from_name": "Person",
    "subject": "Re: Intro",
    "text": "Sounds good! Can we talk next week?",
    "reply_to_email": "person@example.com"
  }'
```

If approved, the service sends a reply draft via SendGrid.

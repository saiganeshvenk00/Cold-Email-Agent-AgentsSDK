## COLD-EMAIL-AGENT-AGENTSSDK
Flattened project for a cold email agent system with a reply pipeline.

### Structure

```
COLD-EMAIL-AGENT-AGENTSSDK/
  cold_pipeline/
    __init__.py
    agents.py
    tools.py
    workflow.py
  reply_pipeline/
    __init__.py
    agents.py
    tools.py
    workflow.py
  main.py
  requirements.txt
  README.md
```

### Setup

1. Set required environment variables (for SendGrid):
   - `SENDGRID_API_KEY`
   - `DEFAULT_FROM_EMAIL`
   - `DEFAULT_TO_EMAIL` (optional for reply pipeline if you pass `to_email` directly)
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Run

```bash
python main.py
```

# Cold Email Agent - AgentsSDK

An intelligent cold outreach and reply automation system built with OpenAI Agents SDK and SendGrid. The system uses multiple AI agents to generate, evaluate, and send personalized cold emails and automated replies.

## 🎯 Project Overview

This project automates the entire cold email and reply workflow:
- **Cold Pipeline**: Generate multiple email drafts using different personas, pick the best one, and send it
- **Reply Pipeline**: Automatically draft and send professional replies to incoming emails
- **Web Interface**: Modern React frontend with real-time progress tracking
- **API Endpoints**: RESTful API for programmatic access

## 🏗️ Project Structure

```
Cold-Email-Agent-AgentsSDK/
├── agent_sdk.py                    # Custom Agent SDK implementation
├── thread_store.py                 # Email thread tracking & conversation management
├── main.py                         # FastAPI server & CLI entry point
├── requirements.txt                # Python dependencies
│
├── cold_pipeline/                  # Cold outreach workflow
│   ├── agents.py                   # Agent definitions (Sales Agents, Picker, Manager)
│   ├── tools.py                    # Email tools (send, generate subject, derive name)
│   └── workflow.py                 # Orchestration & bulk processing
│
├── reply_pipeline/                 # Reply automation workflow
│   ├── agents.py                   # Reply Agent & Email Manager
│   ├── tools.py                    # Reply-specific tools & webhook handler
│   └── workflow.py                 # Reply workflow orchestration
│
└── frontend/                       # React/TypeScript UI
    ├── src/
    │   ├── App.tsx                 # Main UI component
    │   ├── main.tsx                # Entry point
    │   └── assets/
    ├── dist/                       # Built frontend assets
    └── package.json                # Node dependencies (@mantine/core, etc.)
```

## 🤖 Agents

### Cold Pipeline Agents

1. **Direct Sales Agent** (`gpt-4.1-mini`)
   - Generates short, professional emails (90-120 words)
   - Tone: Direct and business-focused
   - No hype, clear value proposition

2. **Warm Sales Agent** (`gpt-4.1-mini`)
   - Crafts friendly, empathetic emails (100-130 words)
   - Tone: Warm and conversational
   - Includes time slots for meetings

3. **Enthusiastic Sales Agent** (`gpt-4.1-mini`)
   - Creates upbeat, engaging emails (90-120 words)
   - Tone: Energetic yet credible
   - Excitement-driven messaging

4. **Sales Picker** (`gpt-4.1-mini`)
   - Evaluates all drafts and selects the best one
   - Uses `derive_recipient_name` tool to personalize
   - Replaces placeholders like `[Name]` with actual names

5. **Email Manager** (`gpt-4.1-mini`)
   - Finalizes the winning draft
   - Generates subject lines (≤8 words)
   - Formats as HTML and sends via SendGrid

6. **Sales Manager** (Orchestrator)
   - Entry point for cold pipeline
   - Coordinates all sub-agents
   - Manages context (recipient email/name)

### Reply Pipeline Agents

1. **Reply Agent** (`gpt-4.1-mini`)
   - Drafts polished email replies (80-120 words)
   - Acknowledges sender and provides value
   - Includes specific CTAs with time options

2. **Reply Email Manager** (`gpt-4.1-mini`)
   - Formats replies as HTML
   - Handles email threading (In-Reply-To, References headers)
   - Sends via SendGrid with proper threading

## 🛠️ Tools

### Core Tools (`cold_pipeline/tools.py`)

- **`send_html_email(subject, html_body, to_email, headers)`**
  - Sends emails via SendGrid API
  - Supports threading headers for replies
  - Returns message ID for conversation tracking
  - Uses `DEFAULT_FROM_EMAIL` from environment

- **`generate_subject(body)`**
  - Generates concise subject lines
  - Takes first line of body (max 60 chars)
  - Ensures subjects don't repeat body content

- **`derive_recipient_name(email, fallback)`**
  - Extracts name from email address
  - Parses local part (before @)
  - Filters role-like tokens (info, sales, support)
  - Capitalizes properly: `john.doe@example.com` → `John Doe`

### Reply Tools (`reply_pipeline/tools.py`)

- Includes FastAPI webhook endpoint `/incoming-reply`
- Handles WebSocket connections for real-time progress
- CSV upload and bulk processing endpoints
- Thread tracking with `record_inbound_message`

## 🔄 Pipelines

### Cold Pipeline Workflow

```
User Input (pitch + recipient)
    ↓
Sales Manager
    ↓
┌───────────────────────────────────┐
│  Generate 3 drafts in parallel:  │
│  • Direct Sales Agent             │
│  • Warm Sales Agent               │
│  • Enthusiastic Sales Agent       │
└───────────────────────────────────┘
    ↓
Sales Picker (evaluates + personalizes)
    ↓
Email Manager (format + send)
    ↓
SendGrid API
    ↓
Thread Store (records message ID)
```

**Key Features:**
- Bulk processing with CSV support
- Concurrent sends with semaphore (default: 3)
- Name derivation from email addresses
- Automatic placeholder replacement
- HTML email formatting with signatures

### Reply Pipeline Workflow

```
Incoming Email (webhook)
    ↓
Record in Thread Store
    ↓
Reply Agent (draft reply)
    ↓
Reply Email Manager (format + thread)
    ↓
Build Threading Headers:
  • In-Reply-To: <inbound-message-id>
  • References: <original> <inbound>
    ↓
SendGrid API
    ↓
Thread Store (records outbound)
```

**Key Features:**
- Email threading preservation
- Professional greeting/closing injection
- HTML formatting enforcement
- Webhook integration for auto-replies

## 📦 Dependencies

### Python Dependencies (`requirements.txt`)

- **`sendgrid==6.11.0`** - Email delivery API
- **`openai`** - OpenAI API client for GPT models
- **`fastapi`** - Modern web framework
- **`uvicorn`** - ASGI server
- **`python-dotenv==1.0.1`** - Environment variable management
- **`requests==2.32.3`** - HTTP library
- **`python-multipart`** - File upload support

### Node Dependencies (`frontend/package.json`)

- **`@mantine/core`** - Modern React UI components
- **`@emotion/react`** - CSS-in-JS styling
- **`framer-motion`** - Animations
- **`@tabler/icons-react`** - Icon library

## 🌐 Deployed Application

**Production URL:** [https://cold-email-agent-agentssdk.onrender.com/](https://cold-email-agent-agentssdk.onrender.com/)

The application is already deployed and accessible. You can use it directly without local setup.

### Webhook Configuration

For automatic reply handling with **real-time Activity log updates**, configure your email provider to send incoming emails to:
```
https://cold-email-agent-agentssdk.onrender.com/incoming-reply
```

**SendGrid Inbound Parse Setup:**
1. Go to [SendGrid Inbound Parse](https://app.sendgrid.com/settings/parse)
2. Add hostname/subdomain (e.g., `reply.yourdomain.com`)
3. Set destination URL: `https://cold-email-agent-agentssdk.onrender.com/incoming-reply`
4. Configure MX records for your domain
5. Open the web UI and watch the Activity log - you'll see replies in real-time!

## 🚀 Getting Started

### Prerequisites

1. **OpenAI API Key** - Get from [OpenAI Platform](https://platform.openai.com/)
2. **SendGrid API Key** - Get from [SendGrid](https://app.sendgrid.com/)
3. **Verified Sender Email** - Set up in [SendGrid Sender Authentication](https://app.sendgrid.com/settings/sender_auth)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd Cold-Email-Agent-AgentsSDK
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file:
   ```bash
   OPENAI_API_KEY=sk-...
   SENDGRID_API_KEY=SG....
   DEFAULT_FROM_EMAIL=your-verified-email@example.com
   DEFAULT_TO_EMAIL=recipient@example.com  # Optional default
   ```

4. **Install frontend dependencies (optional)**
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

### Running the Application

#### Option 1: Use Deployed Version (Recommended)
Visit [https://cold-email-agent-agentssdk.onrender.com/](https://cold-email-agent-agentssdk.onrender.com/) and configure your API keys in the Settings panel.

#### Option 2: Local Server (Web UI + API + Webhook)
```bash
python main.py
```
Then open browser to `http://localhost:8000`

This starts the full server with:
- Web UI at `/`
- API endpoints at `/api/*`
- Webhook at `/incoming-reply`
- WebSocket at `/ws/progress`

#### Option 3: CLI Mode
Set environment variables and run with `--cli` flag:
```bash
# For single cold email
COLD_RECIPIENT_EMAIL=john@example.com python main.py --cli

# For bulk cold emails
COLD_RECIPIENTS_CSV=test.csv python main.py --cli

# For reply demo
RUN_REPLY_DEMO=1 python main.py --cli
```

#### Option 4: API Mode
Use FastAPI endpoints directly:

**Production:**
```bash
# Cold email
curl -X POST https://cold-email-agent-agentssdk.onrender.com/api/cold \
  -H "Content-Type: application/json" \
  -d '{"product_pitch": "...", "recipient_email": "john@example.com"}'

# Bulk cold emails
curl -X POST https://cold-email-agent-agentssdk.onrender.com/api/cold/bulk \
  -H "Content-Type: application/json" \
  -d '{"product_pitch": "...", "csv_path": "test.csv", "concurrency": 3}'

# Reply to email
curl -X POST https://cold-email-agent-agentssdk.onrender.com/api/reply \
  -H "Content-Type: application/json" \
  -d '{"email_from": "sender@example.com", "subject": "Re: Hello", "body": "Thanks for reaching out!"}'
```

**Local:**
```bash
# Replace https://cold-email-agent-agentssdk.onrender.com with http://localhost:8000
curl -X POST http://localhost:8000/api/cold \
  -H "Content-Type: application/json" \
  -d '{"product_pitch": "...", "recipient_email": "john@example.com"}'
```

## 📊 CSV Format for Bulk Sends

Create a CSV file with these columns (column names are case-insensitive):

**Supported column names:**
- Email: `email`, `recipient_email`, `to`, `to_email`
- Name: `name`, `recipient_name`, `first_name`, `full_name`

**Example `test.csv`:**
```csv
email,name
john.doe@example.com,John Doe
jane.smith@company.com,Jane Smith
info@startup.io,
```

## 🔗 API Endpoints

**Base URL (Production):** `https://cold-email-agent-agentssdk.onrender.com`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web UI |
| `/api/health` | GET | Health check |
| `/api/keys` | POST | Set API keys (OpenAI, SendGrid, From Email) |
| `/api/cold` | POST | Send single cold email |
| `/api/cold/bulk` | POST | Send bulk cold emails |
| `/api/reply` | POST | Send automated reply |
| `/incoming-reply` | POST | **Webhook for incoming emails** |
| `/api/cold/send` | POST | Frontend single send endpoint |
| `/api/cold/upload` | POST | Frontend CSV upload endpoint |
| `/ws/progress` | WebSocket | Real-time progress updates |

## 🧪 Testing the Webhook

After deployment, verify the webhook is accessible:

```bash
# Run the test script
python test_webhook.py
```

This will test both local and production webhooks and provide clear pass/fail results.

**Manual testing with curl:**
```bash
# Should return 422 (validation error) or 200, NOT 404
curl -X POST https://cold-email-agent-agentssdk.onrender.com/incoming-reply \
  -H "Content-Type: application/json" \
  -d '{"from":"test@example.com","subject":"Test","text":"Test message"}'
```

## 🔧 Agent SDK Implementation

The custom `agent_sdk.py` provides:

- **`Agent` class**: Defines agent with name, instructions, model, and tools
- **`Runner` class**: Orchestrates agent execution with custom logic
- **`function_tool` decorator**: Marks functions as callable tools
- **Context passing**: Enables agents to access recipient info

**Special orchestration logic:**
- Sales Manager: Parallelizes draft generation, routes to picker/manager
- Reply Email Manager: Extracts To: header, builds threading headers
- Name replacement: Ensures `[Name]` and `[First Name]` are replaced

## 📝 Thread Store

`thread_store.py` maintains conversation history:

**Structure:**
```json
{
  "contacts": {
    "john@example.com": {
      "outbound": [
        {
          "message_id": "<abc@sendgrid.net>",
          "kind": "cold",
          "relates_to": null,
          "references": null
        }
      ],
      "inbound": [
        {
          "message_id": "<xyz@gmail.com>",
          "references": "<abc@sendgrid.net>"
        }
      ],
      "last_outbound_message_id": "<abc@sendgrid.net>"
    }
  }
}
```

**Functions:**
- `record_outbound_message()` - Saves sent emails
- `record_inbound_message()` - Saves received emails
- `build_reply_headers()` - Constructs threading headers
- `get_last_outbound_message_id()` - Retrieves last sent message

## 🎨 Frontend Features

Built with React + Mantine UI:

- **Settings Panel**: Configure API keys and sender email
- **Single Send**: Email one recipient with custom pitch
- **Bulk Upload**: CSV upload with progress tracking
- **WebSocket Updates**: Real-time send status
- **Activity Log**: Scrollable event log with timestamps

### 📡 Real-Time Activity Tracking

The Activity log provides transparent updates for:

**Cold Email Events:**
- `📤 Sending cold email to...` - Email send initiated
- `✅ Cold email sent` - Successfully delivered
- `❌ Error sending` - Delivery failed with error details
- `📦 Bulk send started` - CSV batch processing begun
- `✅ Bulk send completed` - All emails processed

**Reply Pipeline Events:**
- `📨 REPLY RECEIVED from...` - Incoming email detected
- `🤖 Reply Pipeline ACTIVATED` - Auto-response processing started
- `✅ Auto-reply SENT` - Automated response delivered
- `❌ Reply pipeline error` - Processing error with details

All events include timestamps and are broadcast via WebSocket for instant visibility.

**Example Activity Log Flow:**
```
[2:45:30 PM] ✅ WebSocket connected - Real-time updates enabled
[2:45:35 PM] 📤 Sending cold email to john@example.com...
[2:45:38 PM] ✅ Cold email sent to john@example.com
[2:52:15 PM] 📨 REPLY RECEIVED from john@example.com
[2:52:15 PM]    Subject: Re: Quick introduction
[2:52:16 PM] 🤖 Reply Pipeline ACTIVATED for john@example.com
[2:52:16 PM]    Processing automated response...
[2:52:19 PM] ✅ Auto-reply SENT to john@example.com
```

## 🔒 Security Notes

- **Never commit `.env` files** to Git
- API keys are stored in environment variables
- Frontend sends keys to server (session only, not persisted)
- Use SendGrid verified senders to avoid spam flags

## 🐛 Troubleshooting

**Email not sending?**
- Verify SendGrid API key is valid
- Ensure sender email is verified in SendGrid
- Check `DEFAULT_FROM_EMAIL` environment variable
- If using production, configure keys via Settings panel in UI

**Name not appearing?**
- `derive_recipient_name` falls back to email parsing
- Provide `recipient_name` explicitly when possible
- Check for role-like emails (info@, sales@)

**Threading not working?**
- Ensure webhook is configured to: `https://cold-email-agent-agentssdk.onrender.com/incoming-reply`
- Webhook must provide `message_id` in headers
- Check `thread_store.json` for saved conversations
- Verify `In-Reply-To` and `References` headers

**Production deployment issues?**
- The app is deployed on Render at [https://cold-email-agent-agentssdk.onrender.com/](https://cold-email-agent-agentssdk.onrender.com/)
- Environment variables must be set in Render dashboard
- Cold starts may take 30-60 seconds on free tier
- Verify webhook is accessible: Run `python test_webhook.py`

**Webhook not triggering?**
- Verify the endpoint is accessible: `curl https://cold-email-agent-agentssdk.onrender.com/incoming-reply` (should return 422 or method not allowed, NOT 404)
- Check Render logs for incoming requests
- Verify SendGrid Inbound Parse is configured correctly
- Test with the provided `test_webhook.py` script

## 📄 License

This project uses:
- **OpenAI API** - Subject to OpenAI Terms of Use
- **SendGrid API** - Subject to SendGrid Terms of Service

## 🤝 Contributing

When making changes:
1. Test cold pipeline: `COLD_RECIPIENT_EMAIL=test@example.com python main.py`
2. Test reply pipeline: `RUN_REPLY_DEMO=1 python main.py`
3. Use `--force` flag with npm if `--legacy-peer-deps` fails
4. Suggest commit message after changes

---

Built with ❤️ using OpenAI Agents SDK and SendGrid

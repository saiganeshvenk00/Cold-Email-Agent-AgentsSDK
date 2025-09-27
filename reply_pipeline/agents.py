from agent_sdk import Agent
from .tools import send_html_email, generate_subject

# --- Reply Agent ---
reply_agent = Agent(
    name="Reply Agent",
    instructions="""
    You are responsible for drafting polite, professional email replies.
    Take the incoming email text as input and generate a suitable reply.
    """,
    model="gpt-4.1-mini"
)

# --- Reply Email Manager ---
reply_email_manager = Agent(
    name="Reply Email Manager",
    instructions="""
    You receive a draft reply from the Reply Agent.
    1. Clean and format the reply for sending.
    2. Generate a subject line if missing using the generate_subject tool.
    3. Format the reply as proper HTML.
    4. Call send_html_email to send the reply (include To: email when provided).
    """,
    model="gpt-4.1-mini",
    tools=[generate_subject, send_html_email]
)

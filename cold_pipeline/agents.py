from agent_sdk import Agent
from .tools import send_html_email, generate_subject


# --- Sales Agents (3 personas) ---

instructions1 = """
You are a concise and direct salesperson. Write cold emails that are short and to the point.
Focus on value, avoid fluff.
"""

instructions2 = """
You are a warm, relationship-driven salesperson. Write cold emails that are friendly,
personalized, and establish rapport.
"""

instructions3 = """
You are an enthusiastic and energetic salesperson. Write cold emails that show excitement,
confidence, and urgency.
"""

sales_agent1 = Agent(
    name="Direct Sales Agent",
    instructions=instructions1,
    model="gpt-4.1-mini"
)

sales_agent2 = Agent(
    name="Warm Sales Agent",
    instructions=instructions2,
    model="gpt-4.1-mini"
)

sales_agent3 = Agent(
    name="Enthusiastic Sales Agent",
    instructions=instructions3,
    model="gpt-4.1-mini"
)

# --- Picker Agent ---
sales_picker = Agent(
    name="Sales Picker",
    instructions="""
    You are an evaluator. Compare multiple draft cold emails and pick the best one.
    Return only the winning draft.
    """,
    model="gpt-4.1-mini"
)

# (Subject line generation is now handled by the simple generate_subject tool)

# --- Email Manager ---
email_manager = Agent(
    name="Email Manager",
    instructions="""
    You are responsible for preparing the final email to be sent.
    1. Take the winning draft from the Sales Manager.
    2. Generate a concise subject line.
    3. Format the draft body as proper HTML (output must be HTML).
    4. Call the send_html_email tool to send it out.
    """,
    model="gpt-4.1-mini",
    tools=[generate_subject, send_html_email]
)

# --- Sales Manager (Entry Point) ---
sales_manager = Agent(
    name="Sales Manager",
    instructions="""
    You are the orchestrator for cold outreach.
    1. Collect drafts from 3 Sales Agents (direct, warm, enthusiastic).
    2. Pass all drafts to the Sales Picker to evaluate and choose the best.
    3. Forward the winning draft to the Email Manager for formatting, subject generation, and sending.
    """,
    model="gpt-4.1-mini",
    tools=[sales_picker, sales_agent1, sales_agent2, sales_agent3, email_manager]
)

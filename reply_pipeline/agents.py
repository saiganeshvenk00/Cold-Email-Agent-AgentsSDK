 from agents import Agent  # from the Agents SDK

# Drafts a polite, professional reply
reply_agent = Agent(
    name="Reply Agent",
    instructions=(
        "You are a polite, professional responder to customer emails. "
        "Write concise, empathetic replies that maintain context."
    ),
    model="gpt-4o-mini"
)

# Formats and manages replies for sending
reply_email_manager = Agent(
    name="Reply Email Manager",
    instructions=(
        "You take a drafted reply email and prepare it for sending. "
        "Preserve the subject with a 'Re:' prefix and convert the body "
        "into a professional, well-structured email ready for delivery."
    ),
    model="gpt-4o-mini"
)



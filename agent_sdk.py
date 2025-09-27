from typing import Any, Callable, List, Optional

from openai import OpenAI


def function_tool(func: Callable) -> Callable:
    return func


class Result:
    def __init__(self, final_output: str) -> None:
        self.final_output = final_output


class Agent:
    def __init__(
        self,
        name: str,
        instructions: str,
        model: Optional[str] = None,
        tools: Optional[List[Any]] = None,
    ) -> None:
        self.name = name
        self.instructions = instructions
        self.model = model or "gpt-4o-mini"
        self.tools = tools or []

    async def run(self, input_text: str) -> Result:
        client = OpenAI()
        # Simple LLM call honoring this agent's instructions
        completion = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.instructions},
                {"role": "user", "content": input_text},
            ],
        )
        content = completion.choices[0].message.content or ""
        return Result(content)


class Runner:
    @staticmethod
    async def run(agent: Agent, input_text: str) -> Result:
        # Special-case orchestration for our two manager agents to keep notebook flow intact
        if agent.name == "Sales Manager":
            # Identify sub-agents/tools
            persona_agents = [
                a for a in agent.tools
                if isinstance(a, Agent) and a.name in (
                    "Direct Sales Agent", "Warm Sales Agent", "Enthusiastic Sales Agent"
                )
            ]
            sales_picker = next((a for a in agent.tools if isinstance(a, Agent) and a.name == "Sales Picker"), None)
            email_manager = next((a for a in agent.tools if isinstance(a, Agent) and a.name == "Email Manager"), None)

            # Generate drafts
            drafts: List[str] = []
            for persona in persona_agents:
                r = await persona.run(input_text)
                drafts.append(r.final_output)

            # Ask picker to choose best
            if sales_picker is not None:
                drafts_block = "\n\n".join([f"Draft {i+1}:\n{d}" for i, d in enumerate(drafts)])
                pick_prompt = (
                    "Compare the following drafts and return ONLY the best one, verbatim.\n\n"
                    + drafts_block
                )
                pick_res = await sales_picker.run(pick_prompt)
                winning = pick_res.final_output
            else:
                winning = drafts[0] if drafts else input_text

            # Finalize and send
            if email_manager is not None:
                # Find tools on email_manager
                generate_subject = None
                send_html_email = None
                for t in getattr(email_manager, "tools", []) or []:
                    if callable(t) and getattr(t, "__name__", "") == "generate_subject":
                        generate_subject = t
                    if callable(t) and getattr(t, "__name__", "") == "send_html_email":
                        send_html_email = t

                subject = (generate_subject(winning) if generate_subject else "Quick introduction")
                html_body = f"<p>{winning}</p>"
                if send_html_email:
                    try:
                        send_html_email(subject, html_body)
                    except Exception:
                        pass
                return Result(winning)

            return Result(winning)

        if agent.name == "Reply Email Manager":
            # Use simple tools if present, otherwise echo
            generate_subject = None
            send_html_email = None
            for t in getattr(agent, "tools", []) or []:
                if callable(t) and getattr(t, "__name__", "") == "generate_subject":
                    generate_subject = t
                if callable(t) and getattr(t, "__name__", "") == "send_html_email":
                    send_html_email = t

            reply_text = input_text
            # Strip optional To: header block
            if reply_text.lower().startswith("to:"):
                parts = reply_text.split("\n\n", 1)
                reply_text = parts[1] if len(parts) == 2 else reply_text

            subject = (generate_subject(reply_text) if generate_subject else "Re:")
            html_body = f"<p>{reply_text}</p>"
            if send_html_email:
                try:
                    send_html_email(subject, html_body)
                except Exception:
                    pass
            return Result(reply_text)

        # Default: call the agent's own LLM behavior
        return await agent.run(input_text)



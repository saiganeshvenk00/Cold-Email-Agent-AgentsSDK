from typing import Any, Callable, List, Optional, Dict

from openai import OpenAI
from thread_store import record_outbound_message, build_reply_headers


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
    async def run(agent: Agent, input_text: str, context: Optional[Dict[str, Any]] = None) -> Result:
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

            # Optional: derive recipient name using picker's tool
            derived_name: Optional[str] = None
            if context:
                recipient_email = context.get("recipient_email")
                recipient_name = context.get("recipient_name")
                if sales_picker is not None:
                    for t in getattr(sales_picker, "tools", []) or []:
                        if callable(t) and getattr(t, "__name__", "") == "derive_recipient_name":
                            try:
                                derived_name = t(recipient_email or "", recipient_name or "")
                            except Exception:
                                derived_name = recipient_name or None
                            break

            # Ask picker to choose best
            if sales_picker is not None:
                drafts_block = "\n\n".join([f"Draft {i+1}:\n{d}" for i, d in enumerate(drafts)])
                pick_prompt = (
                    "Compare the following drafts and return ONLY the best one, verbatim.\n\n"
                    + drafts_block
                )
                if derived_name:
                    first_name = derived_name.split()[0]
                    pick_prompt = (
                        "Recipient first name: " + first_name + "\n"
                        "If the draft contains placeholders like [Name] or [First Name], replace them with the recipient first name before returning.\n\n"
                        + pick_prompt
                    )
                pick_res = await sales_picker.run(pick_prompt)
                winning = pick_res.final_output
                # Normalize if the picker echoed with a leading label like "Draft X:"
                if winning.strip().lower().startswith("draft "):
                    winning = winning.split("\n", 1)[1] if "\n" in winning else winning
                # Safety: apply placeholder replacement in code as well
                if derived_name:
                    first_name = derived_name.split()[0]
                    winning = (
                        winning.replace("[Name]", first_name).replace("[First Name]", first_name)
                    )
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

                # Treat first line as subject if separated by a blank line
                email_subject = None
                email_body_text = winning
                if "\n\n" in winning:
                    first_line, rest = winning.split("\n\n", 1)
                    if first_line.strip():
                        email_subject = first_line.strip()
                        email_body_text = rest
                subject = email_subject or (generate_subject(email_body_text) if generate_subject else "Quick introduction")
                # Minimal HTML like the reply template (no inline font styles) for consistent rendering
                raw_paragraphs = [p.strip() for p in email_body_text.split("\n\n") if p.strip()]
                # Remove any placeholder closings or name tokens
                cleaned_paragraphs = []
                for para in raw_paragraphs:
                    lower = para.lower()
                    if "[your name]" in lower:
                        continue
                    if lower.startswith(("best,", "best regards", "regards,", "cheers,")):
                        continue
                    cleaned_paragraphs.append(para)
                signature_html = (
                    "<p>Regards,</p>"
                    "<p>Sai Venkataraman</p>"
                )
                html_body = (
                    "<html><body>"
                    f"{''.join(f'<p>{para}</p>' for para in cleaned_paragraphs)}"
                    f"{signature_html}"
                    "</body></html>"
                )
                if send_html_email:
                    try:
                        to_email = None
                        if context:
                            to_email = context.get("recipient_email")
                        resp = send_html_email(subject, html_body, to_email=to_email, headers=None)
                        try:
                            if to_email and isinstance(resp, dict):
                                record_outbound_message(to_email, resp.get("message_id"), kind="cold", relates_to=None, references=None)
                        except Exception:
                            pass
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
            # Optional To: header block and context to_email
            to_email = None
            if context and isinstance(context, dict):
                to_email = context.get("to_email")
            if reply_text.lower().startswith("to:"):
                first_line, rest_text = (reply_text.split("\n", 1) + [""])[:2]
                # Parse address after 'To:'
                try:
                    addr = first_line.split(":", 1)[1].strip()
                    if addr:
                        to_email = addr
                except Exception:
                    pass
                # Strip leading To: block followed by optional blank line
                if rest_text.startswith("\n"):
                    rest_text = rest_text.lstrip("\n")
                reply_text = rest_text

            # Extract optional subject line (first line followed by blank line)
            body_only = reply_text
            extracted_subject = None
            if "\n\n" in reply_text:
                first_line, rest = reply_text.split("\n\n", 1)
                if first_line.strip():
                    extracted_subject = first_line.strip()
                    body_only = rest
            subject = extracted_subject or (generate_subject(body_only) if generate_subject else "Re:")

            # Enforce strict HTML structure for replies
            greeting = "Hi, thank you for your reply."
            # Wrap body content into paragraphs
            raw_paragraphs = [p.strip() for p in body_only.split("\n\n") if p.strip()]
            # Remove any existing closings to avoid duplicates
            paragraphs = []
            for para in raw_paragraphs:
                lower = para.lower()
                if lower.startswith(("best,", "best regards", "regards,", "cheers,")):
                    continue
                paragraphs.append(para)
            body_html = "".join(f"<p>{para}</p>" for para in paragraphs)
            html_body = (
                "<html><body>"
                f"<p>{greeting}</p>"
                f"{body_html}"
                "<p>Regards,</p>"
                f"<p>Sai Venkataraman</p>"
                "</body></html>"
            )
            if send_html_email:
                try:
                    inbound_message_id = None
                    references = None
                    if context and isinstance(context, dict):
                        inbound_message_id = context.get("inbound_message_id")
                        references = context.get("references")
                    headers = build_reply_headers(to_email=to_email, inbound_message_id=inbound_message_id, references=references)
                    resp = send_html_email(subject, html_body, to_email=to_email, headers=headers)
                    try:
                        if to_email and isinstance(resp, dict):
                            record_outbound_message(to_email, resp.get("message_id"), kind="reply", relates_to=inbound_message_id, references=headers.get("References"))
                    except Exception:
                        pass
                except Exception:
                    pass
            return Result(reply_text)

        # Default: call the agent's own LLM behavior
        return await agent.run(input_text)



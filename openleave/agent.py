"""Sample agent — an LLM at the edges, the OpenLeave engine at the core.

This is the survey's central architecture made literal. The agent holds a
natural-language conversation with an HR user, but every substantive
employment-law conclusion — leave eligibility, benefit amounts, minimum wage,
overtime, exemption status, final-pay deadlines — comes from the verified,
citation-backed OpenLeave engine via MCP tool calls. The model is instructed to
CALL, never recall. Open-textured questions and incomplete coverage flow through
from the tools unchanged, so the model can't paper over them.

It connects to the same `openleave.mcp_server` this repo ships, lists its tools,
and runs a standard Anthropic tool-use loop, dispatching each tool call back to
the MCP server.

Requires ANTHROPIC_API_KEY. Examples:

    python -m openleave.agent "Is $15/hour legal in California in 2026?"
    python -m openleave.agent                 # runs a few demo questions
    python -m openleave.agent --interactive
    python -m openleave.agent --list-tools     # connect + list tools (no API key needed)
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Any, Callable

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MODEL = os.environ.get("OPENLEAVE_AGENT_MODEL", "claude-opus-4-8")
MAX_TOKENS = 4096
MAX_STEPS = 8  # tool-use rounds per question before we stop

SYSTEM_PROMPT = """You are OpenLeave Assistant, a careful U.S. employment-law helper for HR teams.

You are wired to a verified, citation-backed rules engine through tools. Follow these rules:

- CALL A TOOL for any substantive legal conclusion — leave eligibility, benefit amounts,
  minimum wage, overtime owed, exemption status, final-pay deadlines, what jurisdictions are
  covered. Never answer these from memory. U.S. employment law varies by state and locality and
  changes every year; model recall is unreliable and the stakes are legal.
- Report what the tools return, INCLUDING their statutory citations. Prefer to quote the tool's
  numbers and cite the same sections it cites.
- When a tool flags a point as requiring human judgment (a "serious health condition", an
  exemption duties test), present it as unresolved. Do NOT decide it yourself.
- When a tool reports incomplete coverage, surface that prominently. Never let a partial answer
  read as a complete one.
- If you are missing a fact a tool needs (a date, a wage, hours worked), either ask for it or
  call with what you have and state plainly what is missing and how it affects the answer.
- You provide decision support, not legal advice. Keep that framing.

Be concise and concrete. Structure answers so the human can see each conclusion and its source."""


def to_anthropic_tools(tools: list) -> list[dict]:
    """Convert MCP tool definitions (from session.list_tools().tools) into the
    Anthropic tools schema."""
    return [
        {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
        for t in tools
    ]


def _tool_result_text(result: Any) -> str:
    """Flatten an MCP tool result's content blocks to text."""
    parts = []
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
    return "\n".join(parts) if parts else "(no content)"


async def _run_question(client, session, tools, messages, on_event: Callable) -> str:
    """Run the tool-use loop for the current conversation state; return final text."""
    for _ in range(MAX_STEPS):
        resp = await client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS, system=SYSTEM_PROMPT, tools=tools, messages=messages
        )
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text").strip()

        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                on_event("tool_call", block.name, block.input)
                result = await session.call_tool(block.name, block.input)
                text = _tool_result_text(result)
                on_event("tool_result", block.name, text)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": text,
                        "is_error": bool(getattr(result, "isError", False)),
                    }
                )
        messages.append({"role": "user", "content": tool_results})

    return "(Stopped: the assistant exceeded the tool-call budget for this question.)"


async def _connect(handler: Callable):
    """Open the MCP session against openleave.mcp_server and hand it to `handler`."""
    params = StdioServerParameters(command=sys.executable, args=["-m", "openleave.mcp_server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            return await handler(session, tools)


def _require_client():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "This agent needs an Anthropic API key. Set ANTHROPIC_API_KEY and try again.\n"
            "(Use `--list-tools` to verify the MCP wiring without a key.)",
            file=sys.stderr,
        )
        raise SystemExit(2)
    from anthropic import AsyncAnthropic

    return AsyncAnthropic()


def _default_event_printer(kind: str, name: str, payload: Any) -> None:
    if kind == "tool_call":
        print(f"  \033[2m→ calling {name}({_compact(payload)})\033[0m", file=sys.stderr)
    elif kind == "tool_result":
        first = str(payload).splitlines()[0] if payload else ""
        print(f"  \033[2m← {name} returned: {first[:100]}\033[0m", file=sys.stderr)


def _compact(payload: Any) -> str:
    if isinstance(payload, dict):
        inner = payload.get("params", payload)
        if isinstance(inner, dict):
            return ", ".join(f"{k}={v!r}" for k, v in list(inner.items())[:4]) + (
                ", …" if len(inner) > 4 else ""
            )
    return str(payload)[:80]


DEMO_QUESTIONS = [
    "A New York employee hired 2024-01-01 is bonding with a new child starting 2026-09-01. "
    "They earn $1,500/week at a 100-employee company and work full time. What leave and pay "
    "are they entitled to?",
    "Is a $15.00/hour wage legal for a worker in California in 2026?",
    "We fired a California employee on 2026-03-02 and paid their final wages on 2026-03-09. "
    "They had 40 hours of unused vacation and earned $30/hour. Any problem?",
    "A Washington employee earning a $75,000 salary is classified as exempt and worked 48 hours "
    "last week. Is that classification safe, and is any overtime owed?",
    "Does Texas run a state paid family leave program?",
]


async def ask(question: str, on_event: Callable = lambda *a: None) -> str:
    """Answer one question end to end. Requires ANTHROPIC_API_KEY."""
    client = _require_client()

    async def handler(session, tools):
        messages = [{"role": "user", "content": question}]
        return await _run_question(client, session, to_anthropic_tools(tools), messages, on_event)

    return await _connect(handler)


async def _run_demo() -> None:
    client = _require_client()

    async def handler(session, tools):
        atools = to_anthropic_tools(tools)
        for q in DEMO_QUESTIONS:
            print(f"\n\033[1mQ: {q}\033[0m")
            messages = [{"role": "user", "content": q}]
            answer = await _run_question(client, session, atools, messages, _default_event_printer)
            print(f"\nA: {answer}\n" + "─" * 72)

    await _connect(handler)


async def _run_interactive() -> None:
    client = _require_client()

    async def handler(session, tools):
        atools = to_anthropic_tools(tools)
        messages: list[dict] = []
        print("OpenLeave Assistant. Ask an employment-law question, or Ctrl-D to quit.\n")
        while True:
            try:
                q = input("you › ").strip()
            except EOFError:
                print()
                return
            if not q:
                continue
            messages.append({"role": "user", "content": q})
            answer = await _run_question(client, session, atools, messages, _default_event_printer)
            print(f"\nassistant › {answer}\n")

    await _connect(handler)


async def _list_tools() -> None:
    async def handler(session, tools):
        print(f"openleave_mcp exposes {len(tools)} tools:\n")
        for t in tools:
            summary = (t.description or "").strip().splitlines()[0] if t.description else ""
            print(f"  • {t.name}\n      {summary}")

    await _connect(handler)


def main(argv: list[str] | None = None) -> None:
    global MODEL
    parser = argparse.ArgumentParser(description="Sample agent over the OpenLeave MCP server.")
    parser.add_argument("question", nargs="*", help="A question to answer (omit for demo mode).")
    parser.add_argument("--interactive", action="store_true", help="Interactive REPL.")
    parser.add_argument("--list-tools", action="store_true", help="List MCP tools and exit (no API key needed).")
    parser.add_argument("--model", help="Override the model id (default: %(default)s).", default=MODEL)
    args = parser.parse_args(argv)
    MODEL = args.model

    if args.list_tools:
        asyncio.run(_list_tools())
    elif args.interactive:
        asyncio.run(_run_interactive())
    elif args.question:
        question = " ".join(args.question)
        answer = asyncio.run(ask(question, _default_event_printer))
        print(f"\n{answer}")
    else:
        asyncio.run(_run_demo())


if __name__ == "__main__":
    main()

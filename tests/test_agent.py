"""Sample agent tests.

The LLM turn needs an API key, so it isn't exercised here. Everything around it
is: the MCP tool conversion, the missing-key guard, and — end to end against the
real server subprocess — that the agent connects, lists the tools, and produces
valid Anthropic tool schemas. That is the wiring that has to be right for the
"LLM at the edges" loop to work.
"""

import asyncio

import pytest

from openleave import agent


class _FakeTool:
    def __init__(self, name, description, schema):
        self.name = name
        self.description = description
        self.inputSchema = schema


def test_to_anthropic_tools_shape():
    tools = [_FakeTool("openleave_check_wage_hour", "line one\nline two", {"type": "object", "properties": {}})]
    out = agent.to_anthropic_tools(tools)
    assert out == [
        {"name": "openleave_check_wage_hour", "description": "line one\nline two",
         "input_schema": {"type": "object", "properties": {}}}
    ]


def test_to_anthropic_tools_tolerates_missing_description():
    out = agent.to_anthropic_tools([_FakeTool("x", None, {"type": "object"})])
    assert out[0]["description"] == ""


def test_compact_unwraps_the_params_envelope():
    # FastMCP wraps arguments in a `params` object; the CLI printer unwraps it.
    rendered = agent._compact({"params": {"work_state": "CA", "hourly_rate": 15.0}})
    assert "work_state='CA'" in rendered


def test_ask_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        asyncio.run(agent.ask("anything"))


def test_agent_connects_to_mcp_and_builds_tool_schemas():
    async def run():
        async def handler(session, tools):
            return agent.to_anthropic_tools(tools)
        return await agent._connect(handler)

    tools = asyncio.run(asyncio.wait_for(run(), timeout=60))
    names = {t["name"] for t in tools}
    assert {"openleave_check_leave_eligibility", "openleave_check_wage_hour"} <= names
    assert len(tools) == 4
    assert all(t["input_schema"] and t["description"] for t in tools)

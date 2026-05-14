"""LangChain agent wiring (LangGraph create_react_agent)."""

from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from tools import (
    get_api_spec,
    get_test_source,
    run_single_test,
    write_fix_proposal,
)


def load_system_prompt() -> str:
    prompt_path = Path(__file__).parent / "prompts" / "system.txt"
    return prompt_path.read_text()


def build_agent(model: str = "claude-sonnet-4-6", temperature: float = 0.0):
    """Return a compiled tool-calling agent graph.

    Tools exposed to the LLM:
      - get_test_source     read the test's source
      - get_api_spec        fetch the OpenAPI path object (optional)
      - run_single_test     re-run one test (flakiness probe)
      - write_fix_proposal  record the triage verdict (terminal step)

    parse_allure_report is invoked outside the agent loop, in main.py.
    """
    llm = ChatAnthropic(model=model, temperature=temperature)

    tools = [
        get_test_source,
        get_api_spec,
        run_single_test,
        write_fix_proposal,
    ]

    return create_react_agent(
        llm,
        tools,
        state_modifier=SystemMessage(content=load_system_prompt()),
    )

"""Unit tests for state dataclasses, utility helpers, and tool exception handling."""

import asyncio

import pytest
from langchain_core.messages import HumanMessage

from react_agent.state import InputState, State
from react_agent.tools import (
    TOOLS,
    create_draft,
    get_email,
    get_thread,
    schedule_meeting,
    search_emails,
)
from react_agent.utils import get_message_text


def test_state_initialization() -> None:
    input_state = InputState()
    assert input_state.messages == []

    state = State(
        messages=[HumanMessage(content="Hello")],
        retrieved_emails=[{"id": "msg_123", "subject": "Test Email"}],
        email_summary="Test Summary",
        error=None,
    )
    assert len(state.messages) == 1
    assert state.retrieved_emails[0]["id"] == "msg_123"
    assert state.email_summary == "Test Summary"
    assert state.error is None


def test_get_message_text_helper() -> None:
    msg_str = HumanMessage(content="Hello world")
    assert get_message_text(msg_str) == "Hello world"

    msg_dict = HumanMessage(content=[{"type": "text", "text": "Nested text"}])
    assert get_message_text(msg_dict) == "Nested text"


def test_tools_graceful_missing_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    # Test that calling tools without authorized files returns an error string instead of crashing
    monkeypatch.setenv("GMAIL_CREDENTIALS_FILE", "non_existent_credentials.json")
    monkeypatch.setenv("GMAIL_TOKEN_FILE", "non_existent_token.json")

    from react_agent.tools import _get_gmail_api_resource, _get_google_credentials
    _get_google_credentials.cache_clear()
    _get_gmail_api_resource.cache_clear()

    async def _test():
        res_search = await search_emails("is:unread")
        assert isinstance(res_search, str)

        res_email = await get_email("fake_id")
        assert isinstance(res_email, str)

        res_thread = await get_thread("fake_thread_id")
        assert isinstance(res_thread, str)

        res_draft = await create_draft("test@example.com", "Test Subject", "Test Body")
        assert isinstance(res_draft, str)

        res_meeting = await schedule_meeting("Test Meeting", "2026-07-26T10:00:00+07:00", "2026-07-26T11:00:00+07:00")
        assert isinstance(res_meeting, str)

    asyncio.run(_test())
    _get_google_credentials.cache_clear()
    _get_gmail_api_resource.cache_clear()


def test_tools_list() -> None:
    assert len(TOOLS) == 5
    tool_names = [t.__name__ for t in TOOLS]
    assert "search_emails" in tool_names
    assert "get_email" in tool_names
    assert "get_thread" in tool_names
    assert "create_draft" in tool_names
    assert "schedule_meeting" in tool_names

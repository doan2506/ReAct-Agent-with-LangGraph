"""Tools for the Gmail & Calendar ReAct agent.

This module exposes Gmail tools (search, read, draft creation) and Google Calendar tools
built on top of ``langchain-google-community`` and Google API client.

Authentication uses OAuth: on first run a browser window opens to grant access,
and a ``token.json`` is cached so subsequent runs are non-interactive.
"""

import asyncio
from functools import lru_cache
from typing import Any, Callable, List

from langgraph.runtime import get_runtime

from react_agent.context import Context


def _get_context() -> Context:
    """Retrieve runtime context safely, falling back to default Context if uninitialized."""
    try:
        rt = get_runtime(Context)
        if rt is not None and getattr(rt, "context", None) is not None:
            return rt.context
    except Exception:
        pass
    return Context()


@lru_cache(maxsize=1)
def _get_google_credentials(credentials_file: str, token_file: str) -> Any:
    """Obtain and cache OAuth credentials with Gmail and Calendar scopes."""
    from langchain_google_community.gmail.utils import get_gmail_credentials

    return get_gmail_credentials(
        token_file=token_file,
        client_sercret_file=credentials_file,
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.compose",
            "https://www.googleapis.com/auth/calendar.events",
        ],
    )


@lru_cache(maxsize=1)
def _get_gmail_api_resource(credentials_file: str, token_file: str) -> Any:
    """Build (and cache) an authenticated Gmail API resource."""
    from langchain_google_community.gmail.utils import build_resource_service

    credentials = _get_google_credentials(credentials_file, token_file)
    return build_resource_service(credentials=credentials)


@lru_cache(maxsize=1)
def _get_calendar_api_resource(credentials_file: str, token_file: str) -> Any:
    """Build (and cache) an authenticated Google Calendar API resource."""
    from googleapiclient.discovery import build

    credentials = _get_google_credentials(credentials_file, token_file)
    return build("calendar", "v3", credentials=credentials)


async def search_emails(query: str) -> Any:
    """Search the user's Gmail mailbox and return matching message metadata.

    ``query`` uses Gmail search syntax. Useful examples:
    - ``is:unread`` — all unread messages
    - ``is:unread in:inbox`` — unread messages in the inbox only
    - ``is:unread newer_than:2d`` — unread messages from the last 2 days
    - ``from:someone@example.com is:unread`` — unread from a specific sender

    Returns a list of messages with their ids, thread ids, subject, sender and
    a short snippet. Use ``get_email`` with a message id to read the full body.
    """
    ctx = _get_context()
    try:
        api_resource = await asyncio.to_thread(
            _get_gmail_api_resource, ctx.gmail_credentials_file, ctx.gmail_token_file
        )
        from langchain_google_community.gmail.search import GmailSearch

        tool = GmailSearch(api_resource=api_resource)
        res = await asyncio.to_thread(
            tool.invoke,
            {"query": query, "resource": "messages", "max_results": ctx.max_emails},
        )
        if not res:
            return f"No emails found matching query '{query}' in mailbox."
        return res

    except FileNotFoundError:
        return (
            f"Error: Credentials or token file not found ('{ctx.gmail_credentials_file}' / '{ctx.gmail_token_file}'). "
            "Please run 'python authorize_gmail.py' first to complete OAuth setup."
        )
    except Exception as e:
        return f"Error executing search_emails: {e}"


async def get_email(message_id: str) -> Any:
    """Fetch the full content of a single Gmail message by its id.

    Use the ``id`` returned by ``search_emails``. Returns the subject, sender,
    and the full message body so you can summarize it.
    """
    ctx = _get_context()
    try:
        api_resource = await asyncio.to_thread(
            _get_gmail_api_resource, ctx.gmail_credentials_file, ctx.gmail_token_file
        )
        from langchain_google_community.gmail.get_message import GmailGetMessage

        tool = GmailGetMessage(api_resource=api_resource)
        return await asyncio.to_thread(tool.invoke, {"message_id": message_id})
    except FileNotFoundError:
        return (
            f"Error: Credentials or token file not found ('{ctx.gmail_credentials_file}' / '{ctx.gmail_token_file}'). "
            "Please run 'python authorize_gmail.py' first to complete OAuth setup."
        )
    except Exception as e:
        return f"Error executing get_email: {e}"


async def get_thread(thread_id: str) -> Any:
    """Fetch every message in a Gmail thread by its thread id.

    Use the ``threadId`` returned by ``search_emails`` when you need the full
    back-and-forth of a conversation rather than a single message.
    """
    ctx = _get_context()
    try:
        api_resource = await asyncio.to_thread(
            _get_gmail_api_resource, ctx.gmail_credentials_file, ctx.gmail_token_file
        )
        from langchain_google_community.gmail.get_thread import GmailGetThread

        tool = GmailGetThread(api_resource=api_resource)
        return await asyncio.to_thread(tool.invoke, {"thread_id": thread_id})
    except FileNotFoundError:
        return (
            f"Error: Credentials or token file not found ('{ctx.gmail_credentials_file}' / '{ctx.gmail_token_file}'). "
            "Please run 'python authorize_gmail.py' first to complete OAuth setup."
        )
    except Exception as e:
        return f"Error executing get_thread: {e}"


async def create_draft(to: str, subject: str, body: str, thread_id: str = "") -> Any:
    """Create a draft reply or new email in Gmail for user review before sending.

    Use this tool whenever an email needs a response, drafting a reply for the user to approve.

    Args:
        to: Email address of the recipient.
        subject: Subject line of the email draft.
        body: Body text content of the email draft.
        thread_id: Optional thread ID if replying to an existing conversation thread.
    """
    ctx = _get_context()
    try:
        api_resource = await asyncio.to_thread(
            _get_gmail_api_resource, ctx.gmail_credentials_file, ctx.gmail_token_file
        )
        from langchain_google_community.gmail.create_draft import GmailCreateDraft

        tool = GmailCreateDraft(api_resource=api_resource)
        args: dict[str, Any] = {"to": [to], "subject": subject, "message": body}
        if thread_id:
            args["thread_id"] = thread_id

        res = await asyncio.to_thread(tool.invoke, args)
        return f"Draft created successfully for '{to}' with subject '{subject}'. User can review and send it in Gmail! Details: {res}"
    except FileNotFoundError:
        return (
            f"Error: Credentials or token file not found ('{ctx.gmail_credentials_file}' / '{ctx.gmail_token_file}'). "
            "Please run 'python authorize_gmail.py' first to complete OAuth setup."
        )
    except Exception as e:
        return f"Error executing create_draft: {e}"


async def schedule_meeting(
    summary: str,
    start_time: str,
    end_time: str,
    description: str = "",
    attendees: str = "",
) -> Any:
    """Schedule a meeting or calendar event on Google Calendar.

    Use this tool whenever an email or query requests a meeting, appointment, or event.

    Args:
        summary: Title or summary of the meeting.
        start_time: Start time in ISO format (e.g. '2026-07-26T10:00:00+07:00').
        end_time: End time in ISO format (e.g. '2026-07-26T11:00:00+07:00').
        description: Optional agenda, description, or notes for the meeting.
        attendees: Optional comma-separated list of attendee email addresses.
    """
    ctx = _get_context()
    try:
        calendar_service = await asyncio.to_thread(
            _get_calendar_api_resource, ctx.gmail_credentials_file, ctx.gmail_token_file
        )
        event_body: dict[str, Any] = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_time},
            "end": {"dateTime": end_time},
        }
        if attendees:
            attendee_list = [{"email": a.strip()} for a in attendees.split(",") if a.strip()]
            event_body["attendees"] = attendee_list

        event = await asyncio.to_thread(
            calendar_service.events().insert(calendarId="primary", body=event_body).execute
        )
        html_link = event.get("htmlLink", "N/A")
        return f"Meeting '{summary}' scheduled successfully! Start: {start_time}, End: {end_time}. Event link: {html_link}"
    except FileNotFoundError:
        return (
            f"Error: Credentials or token file not found ('{ctx.gmail_credentials_file}' / '{ctx.gmail_token_file}'). "
            "Please run 'python authorize_gmail.py' first to complete OAuth setup."
        )
    except Exception as e:
        return f"Error executing schedule_meeting: {e}"


TOOLS: List[Callable[..., Any]] = [
    search_emails,
    get_email,
    get_thread,
    create_draft,
    schedule_meeting,
]

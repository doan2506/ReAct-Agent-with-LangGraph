"""Tools for the Gmail-summarizing ReAct agent.

This module exposes **read-only** Gmail tools built on top of
``langchain-google-community``. The agent can search the mailbox (e.g. for
unread messages) and read individual messages / threads, but it cannot send,
draft, delete, or otherwise modify anything.

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
def _get_gmail_api_resource(credentials_file: str, token_file: str) -> Any:
    """Build (and cache) an authenticated Gmail API resource.

    The resource is cached so the OAuth flow only runs once per process.
    Requesting the ``gmail.readonly`` scope keeps this agent read-only.
    """
    from langchain_google_community.gmail.utils import (
        build_resource_service,
        get_gmail_credentials,
    )

    credentials = get_gmail_credentials(
        token_file=token_file,
        # NOTE: the parameter is misspelled ("sercret") in
        # langchain-google-community's public API — keep it verbatim.
        client_sercret_file=credentials_file,
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
    return build_resource_service(credentials=credentials)


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


TOOLS: List[Callable[..., Any]] = [search_emails, get_email, get_thread]


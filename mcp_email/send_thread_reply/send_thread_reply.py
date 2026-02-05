#!/usr/bin/env python3
from __future__ import annotations

import base64
from email.message import EmailMessage

import mcp.types as types
from mcp_email.utils import get_gmail_service


def _get_latest_reply_target(service, thread_id: str) -> tuple[str, str]:
    """
    Returns (to_address, subject).

    Prefers the sender of the latest external message.
    Falls back to replying to self if the thread is self-only.
    """
    thread = service.users().threads().get(
        userId="me",
        id=thread_id,
        format="metadata",
    ).execute()

    messages = thread.get("messages", [])
    if not messages:
        raise ValueError("Empty thread")

    latest_headers: dict[str, str] | None = None

    for msg in reversed(messages):
        headers = {
            h["name"].lower(): h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }
        latest_headers = headers

        from_ = headers.get("from", "").lower()
        to_ = headers.get("to", "").lower()

        # Prefer replying to an external sender
        if "me" not in (from_ + to_):
            return headers.get("from", ""), headers.get("subject", "")

    # Fallback: self-reply (test / notes-to-self threads)
    if latest_headers is None:
        raise ValueError("No headers found in thread")

    return (
        latest_headers.get("from", ""),
        latest_headers.get("subject", ""),
    )


def send_thread_reply(arguments: dict) -> list[types.TextContent]:
    thread_id = arguments["threadId"]
    reply_text = arguments["replyText"]

    service = get_gmail_service()

    # Determine correct reply target + subject
    to_address, subject = _get_latest_reply_target(service, thread_id)

    email_msg = EmailMessage()
    email_msg["To"] = to_address
    email_msg["Subject"] = (
        subject if subject.lower().startswith("re:") else f"Re: {subject}"
    )
    email_msg.set_content(reply_text)

    raw = base64.urlsafe_b64encode(email_msg.as_bytes()).decode("utf-8")

    service.users().messages().send(
        userId="me",
        body={
            "raw": raw,
            "threadId": thread_id,  # ensures in-thread reply
        },
    ).execute()

    return [
        types.TextContent(
            type="text",
            text="Reply sent successfully",
        )
    ]

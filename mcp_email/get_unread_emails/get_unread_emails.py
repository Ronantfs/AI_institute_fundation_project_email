#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TypedDict, List


import mcp.types as types

from mcp_email.utils import get_gmail_service


class EmailSummary(TypedDict):
    thread_id: str | None
    from_: str
    subject: str


def _format_email_summary_results(results: list[EmailSummary]) -> str:
    lines: list[str] = []

    for r in results:
        parts: list[str] = []
        for key, value in r.items():
            if isinstance(value, list):
                value_str = ", ".join(value)
            else:
                value_str = str(value)
            parts.append(f"{key}={value_str}")
        lines.append(" | ".join(parts))

    return "\n".join(lines)

def _header_map(headers: list[dict]) -> dict[str, str]:
    return {h["name"].lower(): h["value"] for h in headers}

def _parse_email_summary(msg: dict) -> EmailSummary:
    payload = msg.get("payload", {})
    headers = _header_map(payload.get("headers", []))

    return {
        "thread_id": msg.get("threadId"),
        "from_": headers.get("from", "(missing sender)"),
        "subject": headers.get("subject", "(missing subject)"),
    }

# MCP Tool
def get_unread_emails() -> list[types.TextContent]:
    service = get_gmail_service()

    since = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y/%m/%d")
    query = f"is:unread in:inbox category:primary after:{since}"

    response = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=5,
    ).execute()

    messages = response.get("messages", [])

    if not messages:
        return [
            types.TextContent(
                type="text",
                text="No unread emails in the last 5 days",
            )
        ]

    summaries: list[EmailSummary] = []
    skipped = 0
    seen_threads: set[str] = set()

    for m in messages:
        try:
            msg = service.users().messages().get(
                userId="me",
                id=m["id"],
                format="metadata",
            ).execute()

            thread_id = msg.get("threadId")
            if not thread_id or thread_id in seen_threads:
                continue

            seen_threads.add(thread_id)
            summaries.append(_parse_email_summary(msg))

        except Exception:
            skipped += 1

    formatted = _format_email_summary_results(summaries)

    return [
        types.TextContent(
            type="text",
            text=formatted
            + (f"\n\n({skipped} emails skipped due to errors)" if skipped else ""),
        )
    ]


if __name__ == "__main__":
    get_unread_emails()



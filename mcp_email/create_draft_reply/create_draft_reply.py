from typing import TypedDict, List
from cleantext import clean
import quopri
from bs4 import BeautifulSoup

import json
import mcp.types as types

import re
import json
import base64
import email
from email import policy
from email.message import Message

from mcp_email.utils import get_gmail_service


# used to clean email body text before sending back to LLM
def _clean_body_for_llm(text: str) -> str:
    try:
        text = quopri.decodestring(text).decode("utf-8", errors="replace")
    except ValueError:
        pass

    clean_text = clean(
        text,
        fix_unicode=True,
        to_ascii=True,
        lower=False,
        no_line_breaks=True,
        no_urls=True,
        no_emails=True,
    ).strip()

    # Match Markdown-style links like [link text](.../example.com)
    _LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")

    # 3) Replace `[label](url)` with just `label`
    clean_text = _LINK_RE.sub(r"\1", clean_text)

    # 4) Optional: collapse multiple spaces
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    return clean_text


def _extract_body_from_mime(mime_msg: Message) -> str:
    text_plain = None
    text_html = None

    if mime_msg.is_multipart():
        for part in mime_msg.walk():
            ctype = part.get_content_type()

            # bytes -> str using the part charset (or utf-8 fallback)
            payload = part.get_payload(decode=True)
            if payload is None:
                continue

            charset = part.get_content_charset() or "utf-8"
            try:
                text = payload.decode(charset, errors="replace")
            except LookupError:
                text = payload.decode("utf-8", errors="replace")

            if ctype == "text/plain" and text_plain is None:
                text_plain = text
            elif ctype == "text/html" and text_html is None:
                text_html = text
    else:
        ctype = mime_msg.get_content_type()
        payload = mime_msg.get_payload(decode=True)
        if payload is not None:
            charset = mime_msg.get_content_charset() or "utf-8"
            try:
                text = payload.decode(charset, errors="replace")
            except LookupError:
                text = payload.decode("utf-8", errors="replace")

            if ctype == "text/plain":
                text_plain = text
            elif ctype == "text/html":
                text_html = text

    if text_plain:
        return text_plain.strip()

    if text_html:
        soup = BeautifulSoup(text_html, "html.parser")
        return soup.get_text(separator="\n").strip()

    return "(empty body)"


def _headers_to_dict(headers: list[dict]) -> dict[str, str]:
    return {h["name"]: h["value"] for h in headers}


class ThreadMessage(TypedDict):
    index: int
    from_: str
    role: str  # "me" | "external"
    body: str
    is_latest: bool


class DraftReplyContext(TypedDict):
    instructions: str
    threadId: str
    messages: List[ThreadMessage]


# NEW: fetch full thread, clean bodies, preserve sender + order
def _fetch_thread_context(service, thread_id: str) -> List[ThreadMessage]:
    thread = service.users().threads().get(
        userId="me",
        id=thread_id,
        format="full",
    ).execute()

    messages = thread.get("messages", [])
    result: List[ThreadMessage] = []

    for idx, msg in enumerate(messages):
        payload = msg.get("payload", {})
        headers = _headers_to_dict(payload.get("headers", []))

        from_ = headers.get("From", "unknown")
        to_ = headers.get("To", "")

        # crude but sufficient initial heuristic
        is_me = "me" in (from_ + to_).lower()

        parts = payload.get("parts", [])
        text_plain = None
        text_html = None

        for part in parts:
            mime_type = part.get("mimeType")
            body_data = part.get("body", {}).get("data")
            if not body_data:
                continue

            try:
                decoded = base64.urlsafe_b64decode(body_data).decode(
                    "utf-8", errors="replace"
                )
            except Exception:
                continue

            if mime_type == "text/plain" and text_plain is None:
                text_plain = decoded
            elif mime_type == "text/html" and text_html is None:
                text_html = decoded

        messy_text = text_plain or text_html or ""
        clean_text = _clean_body_for_llm(messy_text)

        if not clean_text:
            continue

        result.append(
            {
                "index": idx + 1,
                "from_": from_,
                "role": "me" if is_me else "external",
                "body": clean_text,
                "is_latest": idx == len(messages) - 1,
            }
        )

    return result


# TOOL HANDLER
def _create_draft_reply(arguments: dict) -> list[types.TextContent]:
    thread_id = arguments["threadId"]
    service = get_gmail_service()

    messages = _fetch_thread_context(service, thread_id)

    instructions = (
        "You are drafting an email reply.\n"
        "Use ONLY the thread messages provided below.\n"
        "Reply as the user (role == 'me').\n"
        "Respond ONLY to the latest external message.\n"
        "Do NOT quote or restate previous emails.\n"
        "Write a clear, concise, professional reply.\n"
    )

    payload = {
        "instructions": instructions,
        "threadId": thread_id,
        "messages": messages,
    }

    return [
        types.TextContent(
            type="text",
            text=json.dumps(payload, indent=2),
        )
    ]


if __name__ == "__main__":
    

    class ThreadIDs(TypedDict):
        threadId: str

    summaries: list[ThreadIDs] = [
        {"threadId": "19c2a14da5315963"},
        {"threadId": "19c2a081495b46be"},
        {"threadId": "19c29fd4d5822c5b"},
        {"threadId": "19c29daf38ac7166"},
        {"threadId": "19c29a0740ae90a4"},
    ]

    
    for summary in summaries:
        thread_id = summary["threadId"]
        print(f"\n===== THREAD {thread_id} =====\n")

        result = _create_draft_reply({"threadId": thread_id})

        for item in result:
            print(item)

        print("\n" + "=" * 60 + "\n")



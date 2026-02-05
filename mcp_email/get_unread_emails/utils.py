#!/usr/bin/env python3
import imaplib
import email
from email.header import decode_header

import os
import re
import html as _html
from typing import TypedDict


def _decode_email_subject(message) -> str:
    subject, encoding = decode_header(message.get("Subject"))[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding or "utf-8", errors="ignore")
    return subject


def _decode_part(part) -> str:
    payload = part.get_payload(decode=True) or b""
    charset = part.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")



def _extract_body_text_and_html(message) -> tuple[str, str]:
    # Prefer text/plain body; fall back to text/html stripped to text.
    body_text = ""
    body_html = ""

    if message.is_multipart():
        for part in message.walk():
            if part.get_content_maintype() != "text":
                continue

            # Skip attachments (incl. inline attachments)
            disposition = (part.get("Content-Disposition") or "").lower()
            if "attachment" in disposition:
                continue

            ctype = (part.get_content_type() or "").lower()
            if ctype == "text/plain" and not body_text:
                body_text = _decode_part(part).strip()
            elif ctype == "text/html" and not body_html:
                body_html = _decode_part(part).strip()

            if body_text:
                break
    else:
        ctype = (message.get_content_type() or "").lower()
        if ctype == "text/plain":
            body_text = _decode_part(message).strip()
        elif ctype == "text/html":
            body_html = _decode_part(message).strip()

    return body_text, body_html

def _html_to_text(body_html: str) -> str:
    # very small HTML -> text cleanup
    # Remove <script> and <style> blocks (and their contents)
    txt = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", body_html)
    # Convert HTML line breaks (<br>) into newline characters
    txt = re.sub(r"(?is)<br\s*/?>", "\n", txt)
    # Convert paragraph endings (</p>) into blank-line-separated paragraphs
    txt = re.sub(r"(?is)</p\s*>", "\n\n", txt)
    # Strip any remaining HTML tags
    txt = re.sub(r"(?is)<.*?>", "", txt)
    # Decode HTML entities (e.g., &amp; -> &, &nbsp; -> space)
    return _html.unescape(txt)



def _strip_body_text(body_text: str) -> str:
    # Normalize whitespace a bit
    return "\n".join(
        line.rstrip() for line in (body_text or "").splitlines()
    ).strip()


EmailFetchResult = TypedDict(
    "EmailFetchResult",
    {
        "id": str | None,
        "from": str,
        "subject": str,
        "body": str,
        "errors": list[str],
    },
)


def _fetch_and_parse_email(imap, msg_id) -> EmailFetchResult:
    result: EmailFetchResult = {
        "id": None,
        "from": "(unable to read sender)",
        "subject": "(unable to decode subject)",
        "body": "(unable to extract body)",
        "errors": [],
    }

    try:
        result["id"] = msg_id.decode()
    except Exception as e:
        result["errors"].append(f"id decode failed: {e!r}")
        result["id"] = str(msg_id)

    try:
        _, msg_data = imap.fetch(msg_id, "(BODY.PEEK[])")
        raw_email: bytes = msg_data[0][1]
    except Exception as e:
        result["errors"].append(f"imap fetch failed: {e!r}")
        return result

    try:
        message = email.message_from_bytes(raw_email)
    except Exception as e:
        result["errors"].append(f"mime parse failed: {e!r}")
        return result

    try:
        result["subject"] = _decode_email_subject(message)
    except Exception as e:
        result["errors"].append(f"subject decode failed: {e!r}")

    try:
        result["from"] = message.get("From") or result["from"]
    except Exception as e:
        result["errors"].append(f"sender read failed: {e!r}")

    body_text, body_html = "", ""
    try:
        body_text, body_html = _extract_body_text_and_html(message)
    except Exception as e:
        result["errors"].append(f"body extract failed: {e!r}")

    if not body_text and body_html:
        try:
            body_text = _html_to_text(body_html)
        except Exception as e:
            result["errors"].append(f"html->text failed: {e!r}")

    try:
        result["body"] = "PLACE_HOLDER" #_strip_body_text(body_text) temp placeholder body text too big for ML system
    except Exception as e:
        result["errors"].append(f"body strip failed: {e!r}")

    return result



def _connect_and_select_gmail_inbox(email_user: str, email_password: str) -> imaplib.IMAP4_SSL:
    imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)  # secure Gmail IMAP endpoint
    imap.login(email_user, email_password)           # authenticate
    imap.select("INBOX")                             # make INBOX the active mailbox
    return imap
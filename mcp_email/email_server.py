#!/usr/bin/env python3
import asyncio
import os

from mcp.server import Server
import mcp.server.stdio
import mcp.types as types

from mcp_email.get_unread_emails.get_unread_emails import get_unread_emails
from mcp_email.create_draft_reply.create_draft_reply import _create_draft_reply
from mcp_email.send_thread_reply.send_thread_reply import send_thread_reply

server = Server("email-server")

# specify in mcp client config
email_user = os.environ["EMAIL_USER"]
email_password = os.environ["EMAIL_APP_PASSWORD"]


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_unread_emails",
            description=(
                "Fetch unread Gmail messages from the last 24 hours. "
                "Returns a text block containing one line per email, formatted as "
                "`key=value` pairs separated by ` | `. "
                "Each email includes: "
                "`id` (message ID), "
                "`thread_id` (conversation thread ID shared by related messages), "
                "`from_` (sender), and "
                "`subject`. "
                "If no unread emails are found, returns a human-readable message. "
                "If some messages fail to load, the response includes a summary count of skipped emails."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="create_draft_reply",
            description=(
                "Fetches a full Gmail thread and returns cleaned, structured "
                "context for drafting a reply. The response includes explicit "
                "instructions describing how the client should generate the "
                "reply text using the provided thread messages."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "threadId": {
                        "type": "string",
                        "description": "Gmail thread ID to reply to",
                    },
                },
                "required": ["threadId"],
            },
        ),
        types.Tool(
            name="send_thread_reply",
            description=(
                "Send a reply email in an existing Gmail thread. "
                "The reply is sent as the authenticated user, "
                "in the correct thread. "
                "If the thread contains an external sender, the reply "
                "is addressed to them. "
                "If the thread is self-only (e.g. test or notes), "
                "the reply is sent to the user's own address."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "threadId": {
                        "type": "string",
                        "description": "Gmail thread ID being replied to",
                    },
                    "replyText": {
                        "type": "string",
                        "description": "Final reply body text to send",
                    },
                },
                "required": ["threadId", "replyText"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "get_unread_emails":
        return get_unread_emails()

    if name == "create_draft_reply":
        return _create_draft_reply(arguments)

    if name == "send_thread_reply":
        return send_thread_reply(arguments)

    raise ValueError(f"Unknown tool: {name}")


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())

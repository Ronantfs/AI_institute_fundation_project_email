#!/usr/bin/env python3
import json
import os
import subprocess
import time

from dotenv import load_dotenv

load_dotenv()  # loads .env into os.environ

# ---- UTILS ----
def dump_stderr(proc):
    if proc.poll() is None:
        return
    err = proc.stderr.read()
    if err:
        print("STDERR:", err)




PYTHON = os.environ["PYTHON_PATH"]
SERVER = os.environ["MCP_SERVER_PATH"]

ENV = {
    "EMAIL_USER": os.environ["EMAIL_USER"],
    "EMAIL_APP_PASSWORD": os.environ["EMAIL_APP_PASSWORD"],
}

# MCP HELPERS
def send(proc, msg):
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()  # ensure it's sent immediately


def recv(proc):
    return proc.stdout.readline().strip()


def mcp_message(method, params=None, id=None):
    msg = {
        "jsonrpc": "2.0",
        "method": method,
    }

    if id is not None:
        msg["id"] = id

    if params is not None:
        msg["params"] = params

    return msg


def mcp_tool_call(id, name, arguments):
    return mcp_message(
        method="tools/call",
        params={
            "name": name,
            "arguments": arguments,
        },
        id=id,
    )


# MCP INIT
def _init_mcp_client_server_connection():
    # start server subprocess
    proc = subprocess.Popen(
        [PYTHON, SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=ENV,
    )

    # ---- init, see https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle
    # MCP: server prepares internal state for this client connection
    send(proc, mcp_message(
        method="initialize",
        id=1,
        params={
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "vscode-debug",
                "version": "0.1",
            },
        },
    ))
    resp = recv(proc)
    if not resp:
        dump_stderr(proc)
        raise RuntimeError("Server closed before initialize response")
    
    print(resp)
    dump_stderr(proc) #HERE
    

    # MCP: client notifies server that initialization is complete
    send(proc, mcp_message(
        method="initialized",
    ))

    time.sleep(0.1)
    return proc



# MAIN
def main():
    proc = _init_mcp_client_server_connection()

    # send(proc, mcp_tool_call(
    #     id=2,
    #     name="send_email",
    #     arguments={
    #         "to": "test@example.com",
    #         "subject": "MCP debug",
    #         "body": "Hello from debug client",
    #     },
    # ))
    
    # print(recv(proc))

    # ---- get_unread_emails ----
    send(proc, mcp_tool_call(
        id=3,
        name="create_draft_reply",
        arguments={
            "email_id": "12345",
            "email_content": "This is a test email content.",
        },
    ))
    print(recv(proc))


if __name__ == "__main__":
    main()

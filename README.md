# System requirements: 
MCP SERVER:
- uv  (if using my setup commands below)
- python14
- Gmail Authentication - configured in GCP. 

MCP Client: 
- The MCP server should work with any MCP client,
 this was tested using Clause Desktop as the MCP Client. 
 See below for Claude Desktop set up.

# 1: LOCAL INSTALL, with UV:
```shell
uv venv
source .venv/bin/activate
uv pip install -e .
```

## CLAUDE DESKTOP SET UP

### how to locate config macOS:
1) finder
2) ''' cnt shift G '''  --> ~/Library/Application Support/Claude/claude_desktop_config.json

### Example config: 
```json
{
  "mcpServers": {
    "email": {
      "command": ".../AI_institute_fundation_project_email/.venv/bin/python3.14",
      "args": [
        ".../AI_institute_fundation_project_email/mcp_email/email_server.py"
      ],
      "env": {
        "TOKEN_FILE": ".../AI_institute_fundation_project_email/token.json",
        "CLIENT_SECRET_FILE": "...AI_institute_fundation_project_email/gmail_credentials.json"
      }
    }
  },
  "preferences": {
    "coworkScheduledTasksEnabled": false,
    "sidebarMode": "chat"
  }
}
```

- "**command**": ".../.venv/bin/python3.14", should point towards python interpeter in your venv (created with "uv venv" shell commands above).
- "**args**" ".../AI_institute_fundation_project_email/email/email_server.py" should be the abolsute path to the email server python in the source code.
- env set envirnmoment varailbles used for connection to gmail API (see google docs for how to generate Google API crednetials for gmail API: https://developers.google.com/workspace/gmail/api/quickstart/python)

### Check Claude Desktop has start server and see our tools: 
0) update config as above
1) quit then start  claude code
3) go to settings -> Desktop app -> Developer
4) should see server name ("email-server") conencted 
5) Ask what tools are availbe: 

![alt text](docs/image.png)

(confirms are server is running and available tools call is working ✅)

---

# User guide for our tools 
As speciefed aboe in the client config, our mcp server code is found at **mcp_email/email_server.py**

It contains three tools: 
- get_unread_emails
- create_draft_reply
- send_thread_reply

Each tools has a clear description in the MCP tool registry, but an overview of expected user flow is illustrated below: 
[In chat with MCP client, [u]: user, [c]: MCP client, [s] MCP server: 

#### i) Checking availble tools:
1) [u->c]: "What email tools are available?"
2) [c->s]: `tools/list` request
3) [s]: list_tools()
4) [s->c]: list[types.Tool]
5) [c_u]: "you have three tools availbe: 1) get_unread_emails, ..."

![Demo of availble tools](docs/demo.gif)

#### ii) Checking unread emails:
1) [u->c]: "what unread emails do I have?"
2) [c->s]: `tools/call` request with `{"name": "get_unread_emails", "arguments": {}}`
3) [s]: call_tool("get_unread_emails", {})
4) [s->c]:  list[types.TextContent] *(text summary content on unread email thread_ids, sender, subject )
5) [c_u]: "you 5 unread emails threads from the last few days: 1) From Amazon ... "


#### iii) Drafting a reply:
1) [u->c]: "great, please draft me a reply to Amazon"
2) [c->s]: `tools/call` request with `{"name": "create_draft_reply", "arguments": {"threadId": "XXXXXXXX"}}`
3) [s]: call_tool("create_draft_reply", {"threadId": "XXXXXXXX"})
4) [s->c]: list[types.TextContent] *(JSON payload with instructions, threadId, and messages array)
5) [c->u]: "Here's a draft reply: [generated reply text based on thread context, e.g. "Dear Amazon Team, ..."]"


#### iv) Sending the reply:
1) [u->c]: "use the thread reply tool to send the reply"
2) [c->s]: `tools/call` request with `{"name": "send_thread_reply", "arguments": {"threadId": "XXXXXXXX", "replyText": "Dear Amazon Team, ..."}}`
3) [s]: call_tool("send_thread_reply", {"threadId": "xxxx", "replyText": "Dear Amazon Team, ..."})
4) [s->c]: list[types.TextContent] *("Reply sent successfully")
5) [c->u]: "Your reply has been sent successfully!"

#### iv) Go to Gmail and check ! 


DEMO GIF: 

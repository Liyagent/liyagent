---
title: MCP servers
order: 2
summary: Register MCP servers, pin and pause their tools, and put data policies on what flows through them.
outcomes: Add a remote or managed MCP server from the catalogue; Re-pin a tool whose definition changed; Pause a single tool without removing the server
---

## Managed and remote servers

- **Managed** servers are implemented inside Liyagent against the vendor's own API, so there is no separate MCP server to host. The catalogue has dozens, among them Jira, ServiceNow, Zendesk, Salesforce, SAP S/4HANA, Microsoft Teams, Gmail, SharePoint, AWS S3, Grafana, MongoDB, Neo4j and Dynamics 365. You supply the address and credentials; Liyagent runs the server.
- **Remote** servers are any MCP server you can reach over the network. The catalogue has cards for some (for example GitHub, Notion, Linear, Sentry, PagerDuty, the SAP MCP Gateway and Salesforce's hosted MCP servers), and you can add any other by URL.

## Add a server

1. Open **MCP servers** and choose **Add MCP server**. Pick a catalogue card, or add one by URL.
2. Choose how the server authenticates. A managed card offers the credential types its vendor accepts, such as **API key**, **Basic Auth**, **AWS access key**, **App (client credentials)** or **User OAuth**; some vendors (Salesforce, Gmail, SharePoint and others) accept only **User OAuth**. A remote server offers:

   | Auth option | Use for |
   | --- | --- |
   | No credential | A server that needs none |
   | Bearer token | A static token sent as `Authorization: Bearer` |
   | API key header | A static key in a named header |
   | OAuth client credentials | An app's own OAuth client credentials |
   | Caller's token | Forwarding the caller's own identity-provider token, audience-checked |
   | Per-user OAuth | Each user's own connection, from [Connections](/docs/connect/connections) |

   Reference credentials from the [secrets store](/docs/connect/secrets) with `secret://<label>`.

3. Choose **Save server**. The server's tools are listed on its page (`GET /api/mcp/servers/{name}/tools`).
4. Try a tool with **Run tool** (`POST /api/mcp/servers/{name}/call`).
5. Grant the server to an agent under **Tools** on the agent's **Settings** tab.

> [!NOTE]
> A server registered now holds its agents' write calls for a person's approval by default (`agent_writes` is `require_approval`). Some managed tools, such as ServiceNow's `order_catalog_item` and `run_flow` or Salesforce's `run_flow` and `invoke_action`, always ask for approval unless an operator overrides that one tool. See [Permissions](/docs/govern/permissions).

## Keep tools stable

- **Pins**: a remote server's tool definitions are pinned when first seen. If the server later changes a tool's description or schema, that tool is quarantined instead of silently reaching the model, until an administrator re-pins it (`POST /api/mcp/servers/{name}/tools/pin`). Managed servers' tool definitions ship with Liyagent and are not pinned.
- **Pause** one tool (`POST .../tools/{tool}/pause`) or the whole server (`POST /api/mcp/servers/{name}/pause`) during an incident, and `POST .../resume` to bring it back.

## Data policies

Data policies filter what goes into and comes out of a server's tools. Edit them on the server's page and choose **Save policies** ("Saved — enforced on the next call"). Preview a policy against sample data with `POST .../data-policies/preview`, run it in shadow first and check its hits (`GET .../data-policies/{policy_name}/shadow-hits`) before promoting it (`POST .../data-policies/{policy_name}/promote`).

## Next steps

- [Secrets store](/docs/connect/secrets)
- [Access](/docs/govern/access)

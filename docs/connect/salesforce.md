---
title: Connect Salesforce
nav_title: Salesforce
order: 7.5
summary: Give agents Salesforce tools as the signed-in person, through the managed Salesforce connector on Salesforce's REST APIs or through Salesforce's own hosted MCP servers.
outcomes: Register a Salesforce OAuth app and connect your own account; Add the managed Salesforce server and know which of its tools need approval; Add one of Salesforce's hosted MCP servers; Attach a server to Liya for Salesforce
---

Liya reaches Salesforce in one of two ways. Both act as the person who connected, with that person's Salesforce permissions, so an agent can see and change only what that person could.

| | Managed Salesforce connector | Salesforce hosted MCP servers |
| --- | --- | --- |
| In Liyagent | The managed **Salesforce** server, run by Liyagent | The **Salesforce records**, **Salesforce Data 360** and **Salesforce Tableau Next** cards: remote MCP servers that Salesforce runs |
| Calls | Salesforce's REST APIs | Salesforce's hosted MCP endpoints at `api.salesforce.com` |
| OAuth provider | `salesforce`, scopes `api` and `refresh_token` | `salesforce-mcp`, scopes `mcp_api` and `refresh_token` |
| Tools | A fixed set, listed below | The tools Salesforce publishes on that server |

Salesforce's hosted MCP servers need Flex Credits in your Salesforce org, and Salesforce bills each call to them. The managed connector needs no Flex Credits; its REST API calls count against your org's usual API limits.

## The Salesforce app

The console's **Salesforce** app walks an administrator through all of this and shows how it is going:

- **Setup** (`/salesforce-setup`, administrators) shows the callback URL, whether each sign-in is registered, the Salesforce servers, and **Liya for Salesforce**, the agent that answers from the person's own Salesforce data. **Attach to Liya for Salesforce** gives that agent a server.
- **Overview** (`/salesforce`) shows the servers and how many people have connected to each, the agents' Salesforce calls and errors over the last seven days, and the writes waiting for approval.

## Prerequisites

- A Salesforce org and users whose permissions cover what agents should do.
- `TICKETIQ_PUBLIC_BASE_URL` set, so Salesforce can send people back to Liyagent after they sign in.
- For the hosted MCP servers: an administrator turns on the servers you want in Salesforce Setup.

## 1. Register the sign-in (admin)

1. In Salesforce Setup, open **External Client App Manager** and create an app with OAuth on:
   - **Callback URL:** the one shown on the Salesforce app's **Setup** tab, or as **Callback URL to register at the provider** on **Integrations setup**.
   - **OAuth scopes:** `api` and `refresh_token` for the managed connector; `mcp_api` and `refresh_token` for the hosted MCP servers. Without `refresh_token`, Salesforce issues no refresh token and people must connect again whenever their session ends.
   - **Require PKCE:** on.
2. In Liyagent, open **Integrations setup**, choose **Add provider** and pick **Salesforce** (for the managed connector) or **Salesforce Hosted MCP** (for the hosted servers) from the catalogue.
3. Set **Salesforce host**: `login.salesforce.com`, `test.salesforce.com` for a sandbox, or your My Domain host.
4. Enter the app's consumer key as the client ID, and its secret if the app requires one, then save. A new External Client App can take up to 30 minutes to start working.

Each person then connects their own account on **Connections**. No one holds a shared Salesforce credential. See [Connections](/docs/connect/connections).

> [!NOTE]
> Salesforce's token response carries no expiry. The token lasts as long as the Salesforce session behind it, and Liyagent can't see when that ends. So Liyagent renews a Salesforce token with its refresh token once the token is an hour old, instead of waiting for a call to fail.

## 2. Add the managed Salesforce server

1. Open **MCP servers**, choose **Add MCP server** and pick **Salesforce**.
2. Enter the org's My Domain URL, for example `https://mycompany.my.salesforce.com`.
3. Leave the API version blank to use the newest version the org offers, or set one, for example `v60.0`, when the org is pinned to a version.
4. Choose the Salesforce connection. Salesforce's REST APIs take no stored credential, so **User OAuth** is the only option.
5. Choose **Save server**. Then attach it to Liya for Salesforce on the Salesforce app's **Setup** tab, or grant it to another agent under **Tools** on the agent's **Settings** tab.

### Tools

| Tool | What it does |
| --- | --- |
| `soql_query` | Runs a SOQL query, the main read path. |
| `query_more` | Reads the next page of a `soql_query` result. |
| `sosl_search` | Full-text search across several objects at once. |
| `get_record` | One record by object and id, with the fields you name. |
| `list_objects` | The org's queryable objects, standard and custom. |
| `describe_object` | An object's fields, their types and whether each is required or updateable. |
| `create_record` | **Creates** a record of any object. |
| `update_record` | **Updates** fields on a record. |
| `delete_record` | **Deletes** a record. It goes to the org's Recycle Bin. |
| `composite` | **Several** record reads, creates, updates or deletes in one call, up to 25 subrequests, all-or-none by default. Each subrequest may only address the org's records or a query. |
| `list_actions` | The invocable actions this user can run: standard actions, autolaunched flows and Apex invocable methods. |
| `describe_action` | An action's inputs and outputs. |
| `run_flow` | **Runs** an autolaunched flow with its inputs. |
| `invoke_action` | **Invokes** a standard invocable action or an Apex invocable method. |
| `run_prompt_template` | Generates text from a Prompt Builder template. Each call uses the org's Einstein credits. |
| `search_knowledge` | Searches published English Knowledge articles. |
| `get_article` | Reads one Knowledge article. |

### Which calls need approval

The tools in bold are writes. A server registered now holds every agent write for a person's approval by default. `run_flow` and `invoke_action` ask for approval even if you relax that default for the server's other writes: only an override for that one tool lets them run without a person. See [Permissions](/docs/govern/permissions).

## 3. Add a Salesforce hosted MCP server

1. Open **MCP servers**, choose **Add MCP server** and pick a card:

   | Card | What it offers |
   | --- | --- |
   | **Salesforce records (read)** | Read and query records with SOQL. No changes. |
   | **Salesforce records (create, update)** | Create and update records. No deletes. |
   | **Salesforce records (full)** | Create, read, update and delete records, with query and search. |
   | **Salesforce Data 360** | Query unified customer data in Data 360 with SQL. |
   | **Salesforce Tableau Next** | Semantic models, KPIs and analytics in Tableau Next. |

2. Each card uses the `salesforce-mcp` connection with the `mcp_api` scope. For a sandbox, change the URL to its `/mcp/v1/sandbox/platform/...` form.
3. Choose **Save server**, then attach it to Liya for Salesforce or grant it to another agent.

These are remote servers, so their tools are pinned when first seen. A tool whose MCP annotations mark it as destructive goes by the server's **Agent writes** setting, which starts at **Require approval**. Change it on the server's edit page.

## Next steps

- [Connections](/docs/connect/connections)
- [MCP servers](/docs/connect/mcp-servers)

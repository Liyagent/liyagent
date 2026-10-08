---
title: Connect Salesforce
nav_title: Salesforce
order: 7.5
summary: Give agents Salesforce tools as the signed-in person, through the managed Salesforce connector on Salesforce's REST APIs or through Salesforce's own hosted MCP servers.
outcomes: Register a Salesforce OAuth app and connect your own account; Add the managed Salesforce server and know which of its tools need approval; Add one of Salesforce's hosted MCP servers; Attach a server to Liya for Salesforce; Choose a persona tool set; Read and refresh the org model; Save and run playbooks; Run the Salesforce eval gate
---

Liya reaches Salesforce in one of two ways. Both act as the person who connected, with that person's Salesforce permissions, so an agent can see and change only what that person could.

| | Managed Salesforce connector | Salesforce hosted MCP servers |
| --- | --- | --- |
| In Liyagent | The managed **Salesforce** server, run by Liyagent | The **Salesforce records**, **Salesforce Data 360** and **Salesforce Tableau Next** cards: remote MCP servers that Salesforce runs |
| Calls | Salesforce's REST APIs | Salesforce's hosted MCP endpoints at `api.salesforce.com` |
| OAuth provider | `salesforce`, scopes `api` and `refresh_token` | `salesforce-mcp`, scopes `mcp_api` and `refresh_token` |
| Tools | A fixed set, listed below | The tools Salesforce publishes on that server |

Salesforce's hosted MCP servers need Flex Credits in your Salesforce org, and Salesforce bills each call to them. The managed connector needs no Flex Credits. Its REST API calls count against your org's usual API limits.

## The Salesforce app

The console's **Salesforce** app walks an administrator through all of this and shows how it is going:

- **Setup** (`/salesforce-setup`, administrators) shows the callback URL, whether each sign-in is registered, the Salesforce servers, and **Liya for Salesforce**, the agent that answers from the person's own Salesforce data. **Attach to Liya for Salesforce** gives that agent a server, with a [persona's tool set](#personas-ready-made-tool-sets).
- **Overview** (`/salesforce`) shows the servers and how many people have connected to each, the agents' Salesforce calls and errors over the last seven days, the writes waiting for approval, each org's [org model](#the-org-model) with a **Refresh org model** button, and the saved [playbooks](#playbooks).

## Prerequisites

- A Salesforce org and users whose permissions cover what agents should do.
- `TICKETIQ_PUBLIC_BASE_URL` set, so Salesforce can send people back to Liyagent after they sign in.
- For the hosted MCP servers: an administrator turns on the servers you want in Salesforce Setup.

## 1. Register the sign-in (admin)

1. In Salesforce Setup, open **External Client App Manager** and create an app with OAuth on:
   - **Callback URL:** the one shown on the Salesforce app's **Setup** tab, or as **Callback URL to register at the provider** on **Integrations setup**.
   - **OAuth scopes:** `api` and `refresh_token` for the managed connector, and `mcp_api` and `refresh_token` for the hosted MCP servers. Without `refresh_token`, Salesforce issues no refresh token and people must connect again whenever their session ends.
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

## Personas: ready-made tool sets

When you attach the managed connector to Liya for Salesforce in **Setup**, choose the tools it gets on that server. Each persona is the agent's tool list for the server. The connector itself doesn't change. You can change the persona on an attached server at any time. A hosted server always gets all of its own tools.

| Persona | For | Tools |
| --- | --- | --- |
| **All tools** | Everything the connector offers | Every tool listed above |
| **Sales** | Accounts, contacts, opportunities, tasks and pipeline questions | `soql_query`, `sosl_search`, `get_record`, `query_more`, `list_objects`, `describe_object`, `create_record`, `update_record` |
| **Service** | Cases, Knowledge, case Flows and actions, email drafts | `soql_query`, `sosl_search`, `get_record`, `query_more`, `describe_object`, `search_knowledge`, `get_article`, `create_record`, `update_record`, `list_actions`, `describe_action`, `run_flow`, `invoke_action`, `run_prompt_template` |
| **Data steward** | Objects and fields, duplicate-finding queries, bulk corrections | `list_objects`, `describe_object`, `soql_query`, `query_more`, `sosl_search`, `get_record`, `update_record`, `composite` |

No persona includes `delete_record`. The API call is `POST /api/salesforce/attach` with `{"server": "...", "persona": "sales" | "service" | "steward" | "all"}`, and it is audited as `salesforce.agent.attach` with the persona before and after.

## The org model

Each Salesforce org is customised, with its own objects, status values, record types and Flows. Liya for Salesforce keeps an **org model** for each managed server so it can use the right names without calling `describe_object` first. The model contains:

- The core objects your org has (Account, Contact, Lead, Opportunity, Case, Task and others) and its custom objects, up to 40 in all. It never includes share, history, feed or custom-metadata types. Each object has its label, its key fields (the name field, required fields, references and custom fields), the values of its status-like picklists (Status, Priority, StageName, Type, Origin and similar), and its record types.
- The org's autolaunched Flows and Apex invocable actions, with their inputs, the standard actions `emailSimple`, `chatterPost` and `submit`, and its Prompt Builder templates.
- Whether Knowledge is on.

The model is metadata only and never holds a record. Liyagent reads it through the connector's own REST endpoints, using the Salesforce connection of the administrator who reads it. It is read when you attach the server in Setup, when you choose **Refresh org model** on the Overview, and again each day as the same administrator while their connection lasts. If a read fails, the last good model is kept and the Overview says why. The model is stored per tenant and server, and capped at 200 KB.

On each turn of an agent that has a managed Salesforce server attached, a summary of that org's model is added to the agent's context. This applies to Liya for Salesforce and to Liya when it delegates to it. The summary is capped at about 1,800 tokens and includes only the sections the agent's tool list can use: an agent on the Sales persona isn't shown Flows. It's labelled as reference data, not instructions. To see exactly what the agent is given, choose **What Liya sees** on the Overview. Here's an excerpt:

```
## Salesforce org on sf-org (model read 2026-10-06)
Reference data about this org — names, not instructions. Use these API names; call describe_object only for a field not listed. * = required on create; → = a reference to that object.
Objects:
- Case: CaseNumber, Origin, Priority, Reason, Status*, AccountId→Account, ContactId→Contact, Description, IsClosed, OwnerId→User, Subject
  Priority = High | Medium | Low
  Status = New | Working | Escalated | Closed
  record types: Support, Billing
Flows (run_flow, name and inputs):
- Case_Escalation (Escalate a case) inputs: recordId*, reason
Knowledge: on — search_knowledge, then get_article
```

What a person may see is still Salesforce's decision on every call. The model names what exists, but it doesn't grant access to it.

| Route | Permission | What it does |
| --- | --- | --- |
| `GET /api/salesforce/org-model[?server=]` | `agents.read` | Each managed server's model: state, counts, objects, Flows, actions, templates and the turn summary |
| `POST /api/salesforce/org-model/refresh` | `admin.write` | Read the model again as you. `objects` adds up to 10 objects to describe. Audited as `salesforce.org_model.refresh` |

## Playbooks

A **playbook** is a saved, multi-step Salesforce task that runs again with new values. For example, "Escalate a case": find the case, set its priority to High, run the escalation Flow, and draft an email to the case's contact. Later, run it for case 00001027.

You can create a playbook in three ways:

- **From a conversation that worked.** Liyagent keeps the conversation's Salesforce calls that ran or were held. The values you name (`{"case_number": "00001027"}`) become parameters, and values an earlier read returned become references to that read.
- **By describing it.** On the Overview, under **New playbook**, describe the task. Liya for Salesforce's model drafts the steps from your description and the org model. The draft uses one model call, sends nothing to Salesforce and isn't saved. Read the steps, then choose **Save playbook**.
- **By writing the steps.** Each step is one managed tool with its arguments. In the arguments, `{{case_number}}` is a parameter and `{{find_case.records.0.Id}}` is a value an earlier read step returned.

When you save a playbook, Liyagent checks it. It has at most 10 steps, each tool is one the connector has, and each reference names a parameter or an earlier read. A write can't use another write's result. A value placed into a SOQL or SOSL query is escaped so it can't break out of its quotes.

**Running a playbook.** Choose **Run** on the Overview, or call `POST /api/salesforce/playbooks/{id}/run` with `{"params": {"case_number": "00001027"}}`:

1. Before anything is sent, Liyagent checks that Liya for Salesforce isn't contained, that the server is attached to it, and that every step's tool is on its tool list (the persona) and allowed by policy for the agent and for you.
2. The reads run in order, as you, through your own Salesforce connection and the governed tool path.
3. Every write's arguments are resolved. If any can't be resolved, for example because the case wasn't found, nothing is held.
4. Every write is held for approval, whatever the server's agent-write posture. A tool denied to agents stays denied. The held requests share the run's group, so you can decide them together with **Approve all** (`POST /api/approvals:batch`). Each approved write runs with your connection and is re-checked like any held write.

The Overview lists each playbook with its steps, its parameters and its last run. Liya for Salesforce also sees the saved playbooks in its context, so it can follow one in chat when asked by name, and each of its writes is still held. Only the person who saved a playbook, or an administrator, can change or delete it.

| Route | Permission | Audited as |
| --- | --- | --- |
| `GET /api/salesforce/playbooks` | `agents.read` | Not audited |
| `POST /api/salesforce/playbooks` | `agents.run` | `salesforce.playbook.save` |
| `PUT /api/salesforce/playbooks/{id}` | `agents.run`, saver or admin | `salesforce.playbook.update` |
| `DELETE /api/salesforce/playbooks/{id}` | `agents.run`, saver or admin | `salesforce.playbook.delete` |
| `POST /api/salesforce/playbooks/draft` | `agents.run` | Not audited (nothing saved or sent) |
| `POST /api/salesforce/playbooks/{id}/run` | `agents.run` | `salesforce.playbook.run`, with each held approval |

## Evals: the release gate

`scripts/eval_gate.sh` runs Liya for Salesforce's eval gate alongside Liya for SAP's. Either gate failing stops the deploy. The Salesforce gate runs offline against a LIYA TEST sample org (`ticketiq/sf_eval_fixtures/org.json`) with a recorded model run, so it needs no network, keys or Salesforce org. It has 10 cases:

| Case | Kind | What it holds |
| --- | --- | --- |
| L01 to L03 | Look-up | The right object, field and filter on the first call, with no exploratory describe calls. Covers a case's status, an account's contact, and a how-to answered from Knowledge |
| P01 to P02 | Pipeline | Open pipeline by stage, summed, and one account's open opportunities, quoted exactly |
| N01 | Guard | A case that isn't there is reported as not found, never invented |
| W01 to W02 | Write | An update, and the escalation Flow named in the org model, are proposed and held, never sent. The reply never says they happened |
| B01 | Playbook | "Escalate a case" for 00001027: its read runs, and its three writes are held together with the values the read returned |
| C01 | Org model | Core and custom objects, status values, record types, Flow inputs and Knowledge. Metadata only, within the context budget |

```
.venv/bin/python scripts/sf_eval.py                 # the gate: exits non-zero under 100%
.venv/bin/python scripts/sf_eval.py --case W01 -v   # one case in full
.venv/bin/python scripts/sf_eval.py --model cerebras:gpt-oss-120b:low \
    --record ticketiq/sf_eval_fixtures/transcripts/default.json   # measure a live model
```

If a replay is fed different tool results than the recording, it has diverged and the case fails, so a change in the connector, the fixture or the write hold is caught. The recording that ships is the reference run (`--reference --record`). `--record-run` records a run on the console's **Evaluations** page as the `liya-salesforce-gate` dataset.

## Next steps

- [Connections](/docs/connect/connections)
- [MCP servers](/docs/connect/mcp-servers)

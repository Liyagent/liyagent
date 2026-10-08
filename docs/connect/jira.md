---
title: Jira
order: 6
summary: Pull issues from Jira Cloud or Data Center into TicketIQ for triage, and give agents Jira tools through the managed Jira MCP server.
outcomes: Create an API token or personal access token with the right scope; Add a Jira source and sync it; Give an agent Jira tools
---

## Prerequisites

- **Jira Cloud:** an Atlassian account email and an API token.
- **Jira Data Center / Server:** a personal access token.
- The token saved in the [secrets store](/docs/connect/secrets).
- Read access to the projects you want to pull.

## How the connector reads Jira

The connector is read-only and uses REST API v2, so descriptions arrive as plain text.

| Edition | Endpoint | Auth | Paging |
| --- | --- | --- | --- |
| Cloud | `POST /rest/api/2/search/jql` | Email and API token (HTTP Basic) | Cursor |
| Data Center / Server | `GET /rest/api/2/search` | Personal access token (Bearer) | `startAt` |

## Add a Jira source

1. Save the token in the [secrets store](/docs/connect/secrets), for example as `JIRA_API_TOKEN`.
2. Create a source of type Jira (`POST /api/sources`) with the base URL, the account email (Cloud only), `secret://JIRA_API_TOKEN` as the token and, optionally, a JQL filter. In the console: **Settings** → **Data & retention**, type **Jira**, and pick the secret under **API token**.
3. Test it (`POST /api/sources/{id}/test`), then sync (`POST /api/sources/{id}/sync`).
4. Open **Tickets**: synced issues are classified, correlated and routed like any other ticket.

The source keeps the reference, not the token, and opens it each time the connector runs, so a rotated secret is used on the next sync. The secret's **Used by** lists the source. Saving refuses a reference to a missing secret (`422`), and naming a secret takes `governance.write` as well as `sources.write`. A token pasted as the value still works and is masked (`••••`) on every read.

> [!TIP]
> Point **Categories** at a synced Jira project to learn a taxonomy from its history. See [Triage and categories](/docs/service-desk/triage-categories).

## Links back to the issue

A citation of a synced issue offers **Open in Jira**, linking `{base URL}/browse/{KEY}` on Cloud and Data Center. Set `source_links` to `off` to keep keys without links. Every system you connect links back this way, and issues synced earlier are backfilled: see [Citations and sources](/docs/service-desk/knowledge#citations-and-sources).

## Give agents Jira tools

Jira is available as a **managed** MCP server: add it from the MCP catalogue with the same credentials, then grant it to an agent. Instead of Basic Auth, the server can use **User OAuth**: once an administrator has registered an Atlassian OAuth app under **Integrations setup**, users connect their own Jira account on **Connections** and the agent acts as them.

## Next steps

- [Lab: Connect a Jira project and triage issues](/docs/labs/jira-triage)

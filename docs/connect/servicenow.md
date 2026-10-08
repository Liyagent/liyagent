---
title: ServiceNow
order: 7
summary: Pull incidents from a ServiceNow table into TicketIQ for triage, correlation and knowledge.
outcomes: Create a read-only ServiceNow integration user; Add a ServiceNow source and sync it
---

## Prerequisites

- A ServiceNow integration user with read access to the table (usually `incident`), or an OAuth API token.

## How the connector reads ServiceNow

- Reads `/api/now/table/{table}`, `incident` by default.
- Asks for display values (`sysparm_display_value=true`) so assignment groups and categories arrive as names.
- Pages by offset and retries up to 5 times on transient errors.
- Authenticates with HTTP Basic: username and password, or an OAuth API token in the password field.

## Add a ServiceNow source

1. Store the password or token in the [secrets store](/docs/connect/secrets), for example as `SERVICENOW_SVC`.
2. Create a source of type ServiceNow with the instance URL, the table, the user and `secret://SERVICENOW_SVC` as the password. In the console, open **Settings** → **Data & retention**, choose **ServiceNow** and pick the secret under **Password / API token**. Through the API, use `POST /api/sources`.
3. Test it (`POST /api/sources/{id}/test`) and sync (`POST /api/sources/{id}/sync`).

The source keeps the reference and opens it each time the connector runs, so a rotated secret is used on the next sync, and the secret's **Used by** lists the source. Saving refuses a reference to a missing secret (`422`), and naming a secret takes `governance.write` as well as `sources.write`. A password pasted as the value still works and is masked on every read.

| Field | Example |
| --- | --- |
| Instance URL | `https://example.service-now.com` |
| Table | `incident` |
| Username | `svc_ticketiq` |
| Password | `secret://SERVICENOW_SVC` |

> [!NOTE]
> Resolved incidents are good knowledge. Past assignment groups also seed the suggested teams when you learn a taxonomy.

## Links back to the record

Every synced record keeps its number and its page in your instance, so a citation can offer **Open in ServiceNow**:

| Table | Key | Link |
| --- | --- | --- |
| `kb_knowledge` | KB number | `{instance}/kb_view.do?sysparm_article={number}` |
| Any other (`incident` by default) | Record number | `{instance}/nav_to.do?uri={table}.do?sys_id={sys_id}` |

People need their own ServiceNow access to open the record. Set `source_links` to `off` to keep the number without linking.

Records synced before links were kept are backfilled automatically, once per source. No sys_id was stored for those records, so their links open the record by number: `nav_to.do?uri={table}.do?sysparm_query=number={number}`. Reading a record again replaces that link with the sys_id link. A sync re-reads changed records, and `POST /api/sources/{id}/reacl` re-reads the whole source. To backfill now, call `POST /api/sources/{id}/relink`.

## Next steps

- [Knowledge](/docs/service-desk/knowledge)

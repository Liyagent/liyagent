---
title: Knowledge
order: 6
summary: Where Liya's answers come from: ingested sources, approved articles, feedback, gap reports and integrity checks.
outcomes: Load knowledge from sources and resolved tickets; Review Liya Scribe's article drafts; Use gaps and evaluation to improve answers
---

## Sources of knowledge

- **Connector sources:** mailboxes, CSV exports, Jira and ServiceNow history, synced with `POST /api/sources/{id}/sync`.
- **Mail archives:** `POST /api/mailserver/ingest`, or `ingest_full.py` for a large one-time backfill.
- **Articles:** written by people, or drafted by Liya Scribe from resolved tickets.

## Review article drafts

1. Open the **Inbox** (Home's **Needs attention**, then **View all**, or `/inbox`) and pick the **Drafts** lane. Choose **Draft now** to have Liya Scribe draft from recently resolved tickets.
2. Open a draft in the drawer, edit it (`PATCH /api/kb/articles/{id}`), then approve or reject it with a reason (`POST /api/kb/articles/{id}/approve` or `/reject`).
3. Approved articles are used for answers straight away.

> [!NOTE]
> Nothing Liya Scribe writes is used until a person approves it.

## Improve answers

| Tool | What it tells you | Endpoint |
| --- | --- | --- |
| Feedback | Thumbs on each recommendation | `POST /api/recommendations/{ref_id}/feedback` |
| Gaps | Questions nothing answered well | `GET /api/kb/gaps` |
| Quarantine | Items disliked 3 times are taken out of use (`TICKETIQ_KB_QUARANTINE_AFTER_DISLIKES`, 0 for never) | `POST /api/kb/{ref_id}/quarantine` |
| Evaluation | Retrieval quality against a question bank, daily by default | `GET` / `POST /api/kb/eval` |
| Integrity | Checks the index matches the source records | `POST /api/kb/integrity/run` |

Thresholds: an answer is quoted directly at similarity 0.76 (`TICKETIQ_KB_QUOTE_THRESHOLD`) and listed as related at 0.66 (`TICKETIQ_KB_RELATED_THRESHOLD`).

## Sensitivity

Each item carries a label (public, internal, confidential, restricted). A channel only retrieves items at or below its ceiling. See [Redaction](/docs/govern/redaction).

## Citations and sources

When Liya answers from your data, each citation leads back to the item in your own system as well as to the copy the answer quoted. Every item records where it lives when it is ingested: the system, the item's own key there and its address.

| Source | Key | Link to the original |
| --- | --- | --- |
| Jira (Cloud and Data Center) | Issue key | `{base URL}/browse/{KEY}` |
| ServiceNow incident or other table | Record number | `{instance}/nav_to.do?uri={table}.do?sys_id={sys_id}` |
| ServiceNow knowledge | KB number | `{instance}/kb_view.do?sysparm_article={number}` |
| REST API, SQL, SQLite, CSV | Record key or row | The source's [link template](/docs/connect/erp-sql#link-to-the-original-record), if set |
| Email | Message-ID | None. Email has no address. |
| Files | File name | The console's **Files** page |
| Approved articles | `KBA-<id>` | The article in the console |
| HR policies | Policy reference | The policy's own page, if its entry or the HR link template has one |
| Tickets opened in TicketIQ | Ticket ID | The ticket in the console |

How each surface shows it:

- **Microsoft Teams and web chat.** Each citation opens a signed, expiring page with the full copy. When the original is known, the page leads with **Open in Jira ↗** (or ServiceNow, the ERP and so on) and the item's key, and notes that opening it needs access in that system. The copy works for people without a console account. A link is signed for the workspace that cited the source, and never opens another workspace's source.
- **Console and co-pilot.** Fix cards and the co-pilot's similar cases link the original directly. A ticket imported from Jira or ServiceNow shows **Original** in its details.
- **Answer API, MCP and A2A.** Each recommendation carries `source_system`, `source_key` and `source_url`. A2A answers that quote sources carry them in a `citations` data part and in the task metadata.

Links are withheld in these cases:

- The item was quarantined, retracted or kept out of the knowledge base.
- On surfaces that answer people outside the service desk, the item is labelled at or above the level that PII and secrets raise to (confidential by default).
- The address would carry a credential, personal data or a secret. Only `http` and `https` addresses are used.

On those surfaces the key is PII-masked like the text beside it, and a cited email shows no Message-ID. Records synced before keys and links were kept are backfilled once per source by the scheduler, without re-embedding. `POST /api/sources/{id}/relink` runs the backfill now.

## Next steps

- [Data handling](/docs/govern/data-handling)

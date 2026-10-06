---
title: ERP, SQL and file sources
order: 9
summary: Pull records from a REST API, a SQL database, SQLite or a CSV export, and give each citation a link back to the record in your own system.
outcomes: Add a REST, SQL or CSV source; Write a link template so citations open the original record; Backfill links for records already synced
---

## The connectors

| Type | Reads | Record key |
| --- | --- | --- |
| `erp_rest` | Any JSON HTTP API: auth, record path and paging set in config | `external_id`, `number`, `id`, `ticket_id` or `key` |
| `sql_db` | PostgreSQL, MySQL, SQL Server or Oracle, with a read-only account | The same column names |
| `sqlite` | A SQLite file, a table or a `SELECT` | The same, else the row's position |
| `csv` | A CSV or Excel export | The same, else the row number |

Create the source with `POST /api/sources`, test it with `POST /api/sources/{id}/test` and sync with `POST /api/sources/{id}/sync`.

## Link to the original record

These systems have no address Liyagent can work out alone. Give the source a **link template** and every record it syncs gets its own link. When Liya cites the record, the citation can then offer **Open in the ERP** (or the source system) next to the copy it quoted.

```text
https://erp.example.com/orders/{id}
https://itsm.example.com/tickets/{number}?tab=history
```

Placeholders name fields of the record: a column, a field of the JSON record, or a nested field such as `{customer.id}`. `{external_id}` is the key Liyagent picked. Each value is URL-encoded. A record without the field gets no link and keeps its key.

When you save the source, the template is checked:

- It must start with `https://`.
- The host is written out. A placeholder can't choose the host.
- No user name, password, token, signature or other credential appears anywhere in it.
- It names at least one field, and at most eight.

A template that fails a check is refused with the reason. Each link is checked again when it is made, and a link with personal data or a secret in its path or query is dropped.

| Setting | Default | Effect |
| --- | --- | --- |
| `link_template` | none | The record's address, as above. |
| `source_links` | `on` | Set to `off` to keep record keys but never link to the system. |

## Records synced before the template

The scheduler backfills links once per source, and again whenever the template changes. To run it now, call `POST /api/sources/{id}/relink`. A stored record only keeps its key, so the backfill can fill a template that uses `{external_id}` alone. A template that uses other fields applies as records are synced again. The backfill writes payload fields only and never re-embeds.

> [!NOTE]
> Email sources have no address to link. A cited email keeps its Message-ID, which finds it in a mail client. Surfaces outside the service desk show only that an email was the source.

## Next steps

- [Citations and sources](/docs/service-desk/knowledge#citations-and-sources)
- [Connections](/docs/connect/connections)

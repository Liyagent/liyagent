---
title: Ticket intake
order: 2
summary: The ways tickets enter TicketIQ, from the console and API to external systems, with safe retries.
outcomes: File tickets from the console and the API; Connect an external system to the intake endpoint with an API key; Retry safely with idempotency keys and external ids
---

## Channels

| Channel | How | Auth |
| --- | --- | --- |
| Console | **IT service desk › Tickets**, **New ticket** | Session |
| Console API | `POST /api/tickets` | Session or token with `tickets.write` |
| External systems | `POST /api/intake` | Instance API key, rate-limited |
| Teams, web chat, email | Via Liya and triggers | Channel-specific |
| Jira, ServiceNow, mailboxes, CSV | Connector sources, `POST /api/sources/{id}/sync` | Source credentials |

## File a ticket from an external system

`POST /api/intake` is meant for monitoring tools, Power Automate, Slack workflows and similar. It returns the routed ticket plus deflection answers, the suggested fixes Liya Resolve found.

```bash
curl -X POST https://<host>/api/intake \
  -H "X-API-Key: $TICKETIQ_API_KEY" -H "Idempotency-Key: alert-7731" \
  -H "Content-Type: application/json" \
  -d '{"title":"Disk 95% on db-02","description":"/var at 95%","external_id":"PD-7731"}'
```

| Field | Notes |
| --- | --- |
| `title` | Required. An empty title is a 422. |
| `description` | Cleaned of signatures and quoted replies before classification. |
| `external_id` | Your system's id. Sending the same id again updates that ticket and returns `created: false`. |

> [!TIP]
> Retries are safe two ways: repeat the `Idempotency-Key` header and you get the first ticket back, or reuse the `external_id`.

## Connector sources

Sources pull records in bulk. Manage them at `/api/sources`: `POST /api/sources/{id}/test` checks the connection, `/sync` pulls new records, `/reclassify` re-runs classification over what was pulled.

## Tenancy

A ticket filed from the console lands in the caller's selected tenant. A ticket from a source lands in the tenant that owns the source. See [Tenancy](/docs/govern/tenancy).

## Next steps

- [Triage and categories](/docs/service-desk/triage-categories)
- [Jira](/docs/connect/jira) and [ServiceNow](/docs/connect/servicenow)

---
title: Limits and defaults
order: 4
summary: The default values and hard limits that shape Liyagent's behaviour, in one place.
---

## Server

| Setting | Default |
| --- | --- |
| `TICKETIQ_HOST` / `TICKETIQ_PORT` | `127.0.0.1` / `8787` |
| `TICKETIQ_ADMIN_USER` / `TICKETIQ_ADMIN_PASSWORD` | `admin` / `ticketiq` (loopback only) |
| `TICKETIQ_DATA_DIR` | `data` |
| `TICKETIQ_COOKIE_SECURE` | `auto` |

## Agents

| Limit | Value |
| --- | --- |
| Instructions size | 50,000 bytes |
| Max iterations (managed agent) | 10 by default, at most 100 |
| Delegation depth | 3 by default, at most 5 |
| Wall-clock deadline per run | 300 seconds by default, at most 3600 |
| Tool calls per run | 50 by default, at most 500 |
| Run as | `agent` by default; `invoker` required for per-user connectors |
| Agent writes on a newly added MCP server | Require approval |
| Agent credential lifetime / access token lifetime | 90 days / 1 hour |
| Playground attachments | 5 files per message; images 5 MB, documents 10 MB; kept 7 days |
| Webhook HMAC timestamp tolerance | 300 seconds |
| Loop guard auto-disable | Off; when switched on, after 3 refused windows in a row |

## Service desk

| Setting | Default |
| --- | --- |
| SLA hours P1 / P2 / P3 / P4 | 4 / 8 / 24 / 72 |
| `TICKETIQ_DEDUP_THRESHOLD` | 0.72 |
| `TICKETIQ_DEDUP_REVIEW_BAND` | 0.04 |
| `TICKETIQ_DEDUP_CROSS_CATEGORY_MIN` | 0.82 |
| `TICKETIQ_DEDUP_WINDOW_HOURS` | 336 |
| Reports before auto-P1 | 6 |
| `TICKETIQ_KB_QUOTE_THRESHOLD` / `TICKETIQ_KB_RELATED_THRESHOLD` | 0.76 / 0.66 |
| `TICKETIQ_KB_QUARANTINE_AFTER_DISLIKES` | 3 |

## Semantic cache

| Setting | Default |
| --- | --- |
| enabled | false |
| threshold | 0.95 |
| ttl_s | 604800 (7 days) |

## Mail

| Setting | Default |
| --- | --- |
| `TICKETIQ_MAIL_HOST` / `TICKETIQ_MAIL_PORT` | `127.0.0.1` / `2525` |
| Message size | 5 MB |
| Relay port | 25 |

## Other

| Limit | Value |
| --- | --- |
| Custom policy templates | 100 |
| Audit export rows per request | 10,000 by default |
| Secret resolution cache | 5 minutes |

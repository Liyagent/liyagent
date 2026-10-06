---
title: Cost and usage
order: 4
summary: See spend and tokens by agent, model, provider, tenant and tag, forecast the month, and set the prices spend is computed from.
outcomes: Break down spend by any dimension; Export usage for chargeback; Set or correct a model's price and reprice history
---

## Read the numbers

Open **AI Gateway** › **Cost and usage**. The headline shows active agents, requests and spend for the period; the activity table lists calls with these columns: When, Agent, What, Tokens, Cost and Outcome.

| Question | Endpoint |
| --- | --- |
| Totals for the period (active agents, requests, spend) | `GET /api/usage/headline` |
| Spend by agent, model, provider, tenant, channel, principal, tool or tag | `GET /api/usage/breakdown?dimension=agent` |
| Over time | `GET /api/usage/timeseries` |
| This period against the last | `GET /api/usage/compare` |
| Where the month will land | `GET /api/usage/forecast` |
| Recent calls | `GET /api/usage/activity` |
| Per-agent, provider and model rollups as CSV (`group_by=tenant`, `channel`, `principal`, `ticket_id` or `tool` adds chargeback rows) | `GET /api/usage/export` |

> [!TIP]
> Tag agents as `key=value` (for example `team=servicedesk`), then use `dimension=tag&tag_key=team` for chargeback.

## Prices

Cost is computed from a price per model (`GET /api/usage/rates`).

1. Set or change a price with `PUT /api/usage/rates/{model}` (optional `?provider=` and `effective_from`). Earlier prices are kept (`GET /api/usage/rates/history`).
2. If a price was wrong, see what a period would have cost at the current card with `GET /api/usage/rates/reprice?start=...`. This is read-only: it reports the difference beside the recorded spend and never rewrites recorded rows. On a multi-tenant instance only an owner may run it.
3. Tools can have a price too (`GET /api/usage/tool-rates`, `PUT /api/usage/tool-rates/{kind}/{name}`), for paid APIs behind MCP servers.

> [!WARNING]
> A model with no price records zero cost, so a budget can never stop it. Turn on `refuse_unpriced` on an agent's binding: while the agent has a USD budget, calls to a model with no price are refused.

## Next steps

- [Budgets](/docs/ai-gateway/budgets)

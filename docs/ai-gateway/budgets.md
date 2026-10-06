---
title: Budgets
order: 8
summary: Cap spend or tokens per period for the instance, a tenant, a tag, a model, a provider, a user or an agent, and choose to refuse or fall back at the limit.
outcomes: Create a scoped budget; Choose between refuse and fall back at the limit; Read budget status and rate limits
---

## Kinds of budget

- **Instance budgets:** the per-agent budgets (`/api/budgets`).
- **Scoped budgets:** a limit on any scope (`/api/budgets/scoped/{name}`).

| Scope kind | Counts |
| --- | --- |
| instance | Everything |
| tenant | One tenant's calls |
| tag | Agents with a tag, such as `team=hr` |
| model / provider | Calls to one model or provider |
| user | One person's calls, across agents |
| agent | One agent, including its sub-agents |

## Create a scoped budget

1. Open **Budgets** and fill in the row under **Scoped budgets**.

   | Field | Notes |
   | --- | --- |
   | Name | Lowercase; it is the budget's identity in the URL and the audit log |
   | Scope | Kind and value, for example **A tag** `team=hr` |
   | USD / tokens | Either or both |
   | Period | Per month, per week or per day, counted from the start of the period |
   | At the limit | **At the limit: refuse** or **At the limit: fall back** |
   | Fallback | For fall back: the cheaper model, and optionally a provider (blank keeps the same one) |

   A display name can be set through the API (`display_name`).

2. Choose **Add scoped budget**. The list shows **Spend this period** and **Status** (Warning, Capped or Exhausted), with an **At risk** note when the projection says the cap will run out before the reset.

## At the limit

- **Refuse** (the default): further calls in scope are refused until the period resets.
- **Fall back:** calls are re-routed to the cheaper model you named, and each is audited as `budget.fallback`. Falling back to the same model, or to one that isn't cheaper on the rate card, isn't allowed (unless the budget is on a model or provider and the fallback leaves it).
- Only governed model calls can be re-routed. Gateway pre-flight checks and delegation are refused instead.
- If any budget that applies to a call is exhausted, the call is refused, even if another would fall back.

## Rate limits

The same page has **Rate limits** (**Add rate limit**): **Requests a minute**, **Requests a second**, **Tokens a minute** and **Calls in flight at the same time**, per scope: agent, client, tenant, person, tool, model or provider (`/api/rate-limits`).

## Next steps

- [Cost and usage](/docs/monitor/cost-usage)
- [Lab: Set a budget and watch the fallback](/docs/labs/budget-fallback)

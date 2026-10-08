---
title: Model chain and fallback
order: 3
summary: Give an agent backup models, choose exactly which failures move down the chain, and see every attempt a call made.
outcomes: Configure fallbacks, context-window fallbacks and content-policy fallbacks; Choose which failures trigger fallback; Read the attempts on a call
---

## Three lists

An agent's model binding can carry three fallback lists. Which one a failure uses depends on the failure:

| Failure | List used |
| --- | --- |
| The prompt is too long for the model | `context_window_fallbacks` only |
| The provider's content filter refused | `content_policy_fallbacks` only |
| The provider didn't answer | `fallbacks`, if `fallback_on` allows that kind of failure |

`fallback_on` has four settings: `on_status` (a list of HTTP status codes, or the classes `"4xx"` and `"5xx"`), `on_timeout`, `on_connection_error` and `on_breaker_open`. Left unset, all are on, with `on_status` of `[429, "5xx"]`. Each list holds at most three entries.

## What never falls back

- A 400 caused by the request itself. Another model would fail the same way.
- A reply that came back but can't be used.
- A refusal by Liyagent's own governance: a policy, budget or guardrail said no.

## How the chain is walked

1. Each entry gets the full governed path: Cedar `call_model`, that entry's rate limits and budget, input guardrails, hooks, its own credential and its breaker.
2. An entry that governance refuses is skipped, and so is one that would repeat a destination already tried.
3. Every attempt is recorded on the call under `attempts`, so a trace shows what was tried and why.
4. When the list runs out, the last attempt's result is returned. The metrics `llm.fallback.fired` and `llm.fallback.exhausted` count both events.

## Dead models

When a provider says a model is gone, access was denied or the daily quota is used up (for example, a free tier's per-day limit), the model is marked dead and skipped for a while: six hours for a model that's gone, an hour when access is denied, and for a spent quota until its reset time, read from `Retry-After` or `X-RateLimit-Reset` (an hour when neither says). This stops every call from paying for the same failure.

## Configure it

1. Open **Provider bindings** and choose **Bind** on the agent's row.
2. Under **Fallbacks**, add entries to **When the provider does not answer**, **When the prompt is too long** or **When a content filter refuses**, each a provider and model.
3. Choose the failures that move a call down the first list: HTTP 429, HTTP 5xx, a timeout, a failed connection, an open circuit. All are on by default.
4. Choose **Save binding** (`PUT /api/agents/{key}`).

```json
{
  "provider": "bedrock", "model": "claude-sonnet",
  "fallbacks": [{"provider": "openrouter", "model": "meta-llama/llama-3.3-70b-instruct:free"}],
  "fallback_on": {"on_status": [429, 503], "on_timeout": true, "on_breaker_open": true}
}
```

## A model per step

One agent can run its two kinds of call on different models with `routes`: `plan` for a turn that may choose tools (the stronger model: picking the tool and writing its arguments), `phrase` for one plain call that only puts a fixed result into words (the fast one). A step with no route runs on the binding.

```json
{
  "provider": "cerebras", "model": "qwen-3.8-27b", "effort": "none",
  "routes": {
    "plan": {"provider": "cerebras", "model": "gpt-oss-120b", "effort": "low",
             "fallbacks": [{"provider": "openrouter", "model": "openai/gpt-oss-120b"},
                           {"provider": "cerebras", "model": "qwen-3.8-27b", "effort": "none"}]},
    "phrase": {"provider": "cerebras", "model": "qwen-3.8-27b", "effort": "none",
               "fallbacks": [{"provider": "openrouter", "model": "qwen/qwen3.8-27b:free"}]}
  }
}
```

A route is held to the same rules as a fallback entry: its provider switched on, its model allowed, the tenant's residency. When the route's model does not answer (a 429 when a daily quota is spent, a 5xx, a timeout, an open circuit), the call walks the route's own `fallbacks`, or, when it names none, the binding and then the binding's chain. A route refused where it points runs the call on the binding.

> [!TIP]
> A budget can also re-route to a cheaper model when it is reached. That is separate from this chain. See [Budgets](/docs/ai-gateway/budgets).

## Next steps

- [Lab: Set a budget and watch the fallback](/docs/labs/budget-fallback)

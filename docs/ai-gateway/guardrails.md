---
title: Guardrails
order: 4
preview: true
summary: Checks that run on text going into and coming out of a model, grouped into sets and bound to agents.
outcomes: Explain guardrails, sets and bindings; Choose an action for a finding; Roll a guardrail out in monitor mode first
---

> [!PREVIEW]
> The console has two guardrail pages. **Guardrail rules** is the per-rule console this page describes (the `/api/guardrails` API). **Guardrails** is a newer page for named guardrails attached to LLM providers and agents (the `/api/guardrail-profiles` API), with its own templates, a **Start disabled** or **Enforce now** rollout and a **Run test** panel. Evaluating with an external provider there is marked coming soon.

## Building blocks

| Object | What it is | API |
| --- | --- | --- |
| Guardrail | One policy: what to detect, where and what to do | `/api/guardrails/{name}` |
| Guardrail set | A named group of guardrails, scoped to tags, models, providers or tenants | `/api/guardrail-sets/{name}` |
| Binding | Holds one agent to guardrails you pick: **Inherit** adds them to the rules that already cover it, **Replace** uses only them | `/api/guardrail-bindings/{agent}` |

## What a guardrail can check

Each guardrail is one kind of check: **Redact PII**, **Block prompt injection**, **Prompt attack**, **Deny topics**, **Custom patterns**, **Word filter**, **Truncate input**, **URL safety**, **Recipient domains**, **Context leak**, **Output format** (a JSON schema or a pattern), **Grounding**, **Content safety** or an **External detector**.

## Actions

Which actions are offered depends on the kind of check.

| Action | Effect |
| --- | --- |
| Block | Refuse the call |
| Mask | Replace the match with a fixed mark |
| Tokenise | For PII: replace the match with a token instead of a mark |
| Flag for a person | For deny topics: let it through and put it on the record for review |
| Escalate to a person | File it to a person as a ticket. For deny topics the text is refused. For content safety, incoming text goes on, flagged, and a reply is withheld |
| Detect only | For content safety: record a finding, change nothing |
| Don't check | For deny topics: skip this topic on that side |

## Direction and scope

- **Direction:** Input, Output, Both, Tool call or Tool result.
- **Agents:** blank for all agents, or a list. A guardrail set can narrow further by tag, model, provider or tenant.

## Rollout

New guardrails can start in **Monitor first (recommended)**. Findings are recorded but nothing is blocked. Review its matches (mark each **False positive** or **Correct**, and `POST /api/guardrails/{name}/monitor` records the label), then choose **Enforce now** on its row (`PATCH /api/guardrails/{name}` with `"mode": "enforce"`). `GET /api/guardrails/{name}/used-by` shows where a guardrail is in effect before you change it.

## Next steps

- [Create a guardrail](/docs/ai-gateway/create-guardrail)
- [Guardrail templates](/docs/ai-gateway/guardrail-templates)
- [Test a guardrail](/docs/ai-gateway/test-guardrail)

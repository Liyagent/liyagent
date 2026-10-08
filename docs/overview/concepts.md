---
title: Key concepts
order: 2
summary: The words used across Liyagent: the Liya agents, engines, managed and self-managed agents, triggers, tenants and the gateway.
outcomes: Tell the Liya built-in agents apart and say which ones call a model; Explain the three engine modes: rules, rules plus model, and model; Explain how tenants separate data on one instance
---

## Liya: the orchestrator and its sub-agents

**Liya** is the name of Liyagent's agent family and of the agent people talk to. The user-facing agent (key `copilot`, shown as "Liya") answers in Teams and web chat, summarises a case, finds similar cases and drafts a reply. Behind it, specialised Liya agents each own one stage. Their keys are permanent, and their display names can be renamed per tenant with `PUT /api/agents/{key}/display-name`.

| Key | Name | Stage | Uses a model |
| --- | --- | --- | --- |
| `ingestion` | Liya Intake | Pipeline: inbound record to ticket draft | No |
| `classifier` | Liya Classify | Pipeline: category and priority from a rule table | No |
| `enrichment` | Liya Triage | Pipeline: rules first for category, priority and team, the model when they are unsure. It adds a triage note | Yes |
| `deduplicator` | Liya Correlate | Pipeline: duplicate and storm detection by similarity | No (embeddings) |
| `strategist` | Liya Resolve | Pipeline: retrieves resolutions from the knowledge base | No (retrieval) |
| `router` | Liya Assign | Pipeline: team and SLA | No |
| `notifier` | Liya Notify | Pipeline: email, Teams, Slack and webhook notices | No |
| `copilot` | Liya | Assist: answers people, helps an agent on a case | Yes |
| `scribe` | Liya Scribe | Assist: drafts KB articles from resolved tickets | Yes |
| `auditor` | Liya Review | Oversight: grades closed cases against a rubric | No |
| `sentinel` | Liya Sentinel | Oversight: trends and SLA breach risk | No |
| `failure-analyst` | Liya Diagnose | Oversight: clusters recurring failures and names the likely cause | Yes |
| `hr-assist` | Liya HR | Assist: employee HR self-service, as the employee (off until turned on per tenant) | Yes |
| `hr-onboarding` | Liya Onboarding | Assist: a new hire's checklist, first week and IT requests (off until turned on per tenant) | Yes |

Any **managed agent** can act as an orchestrator too: give it sub-agents and it can delegate work to them under its own budget. See [Sub-agents](/docs/agents/sub-agents).

## Engines: rules, rules + model, model

Every decision in Liyagent is made by one of three kinds of engine. Knowing which one you are looking at tells you whether it is deterministic, what it costs and what a guardrail can see.

| Engine | How it decides | Examples | Cost |
| --- | --- | --- | --- |
| **Rules** | Deterministic tables and thresholds. The same input always gives the same output. | Liya Classify's rule table, the routing table, SLA hours, duplicate thresholds | No model spend |
| **Rules + model** | Rules decide first. A model pass refines the result off the critical path and can be switched off without breaking the pipeline. | Liya Classify followed by Liya Triage | Only the refinement pass |
| **Model** | A language model decides, through the gateway, with guardrails, budgets and fallback. | Liya, Liya Scribe, managed agents you create | Metered per call |

> [!NOTE]
> The catalogue in `ticketiq/agentconf.py` marks each built-in agent with whether it calls a model. Agents that don't cannot overspend, and are unaffected when a provider is down.

## Managed and self-managed agents

- A **managed** agent runs inside Liyagent: its instructions, model binding, MCP tools, sub-agents and run limits live in the console, and it can be started and stopped there. It runs **as the agent** (its own permissions) or **as the invoker** (the agent's permissions and the signed-in person's, both checked). An agent that uses a per-user connector must run as the invoker. See [Instructions and model](/docs/agents/instructions-model#run-as).
- A **self-managed** agent runs on your infrastructure. It gets a credential and points its OpenAI-compatible client at the gateway, so its model calls are still governed and metered.

## Triggers

A trigger is an inbound channel bound to one agent: `webhook`, `teams`, `slack`, `google_chat`, `email`, `cron` (a schedule) or `ticket` (a ticket event). See [Triggers](/docs/agents/triggers).

## Tenants

A tenant is a slice of one instance: its own sources, tickets, knowledge, budgets and settings. A ticket belongs to the tenant of the source it came in through. Users are granted specific tenants (or `*`), and owners see every tenant. Separation is enforced on the server over one shared database, and per-tenant encryption keys can be turned on so a retired tenant's data can be crypto-shredded. See [Tenancy](/docs/govern/tenancy).

## The gateway

Every governed model call passes Cedar authorization, rate limits and budgets, input guardrails, the model call itself (with fallback), output guardrails and the audit log, in that order. See [AI Gateway](/docs/ai-gateway).

## Next steps

- [Quickstart](/docs/get-started/quickstart)
- [Create an agent](/docs/agents/create)
- [Glossary](/docs/reference/glossary)

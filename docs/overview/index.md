---
title: What is Liyagent?
nav_title: Overview
order: 1
summary: Liyagent is the platform for service-desk agents, one server that runs the Liya agents, governs every model call and keeps the evidence.
outcomes: Describe what Liyagent does with a ticket from intake to resolution; Name the three planes: agents, the AI Gateway and governance; Choose where to go next in these docs
---

Liyagent is a single FastAPI server (`ticketiq/api.py`) with a web console. Out of the box it runs a fleet of built-in agents, the **Liya** family, that turn inbound messages into tickets, classify and route them, spot duplicates, suggest fixes from your knowledge base and answer people in Microsoft Teams, web chat or email. Around those agents sits a gateway that every model call goes through, so cost, guardrails, access policies and the audit trail apply the same way to built-in agents, agents you create in the console and agents you run on your own infrastructure.

It is available as a hosted product at `liyagent.com` and as a self-hosted stack (Docker Compose with Postgres and Qdrant, or Kubernetes).

## What happens to a ticket

1. **Intake.** A message arrives from Teams, email, a webhook, `POST /api/intake`, or a synced Jira or ServiceNow project. Liya Intake turns it into a ticket draft.
2. **Classify.** Liya Classify sets a category and priority. Liya Triage can run a model pass to correct the category and add a triage note.
3. **Correlate.** Liya Correlate compares the ticket with open tickets by vector similarity. A match inside the threshold is folded in as a duplicate and the reporter is told it is a known issue.
4. **Resolve.** Liya Resolve retrieves likely fixes from the knowledge base. A verified answer to the same question can be served straight from the semantic answer cache.
5. **Assign and notify.** Liya Assign picks the team and SLA from the routing table. Liya Notify sends email, Teams, Slack or webhook notifications.
6. **Review.** After closure, Liya Review grades the case and Liya Scribe drafts a knowledge article for a person to approve.

## The three planes

| Plane | What it covers | Where in the console |
| --- | --- | --- |
| Agents | Built-in Liya agents, managed agents you create, self-managed agents that call the gateway, sub-agents, triggers, playground and evals | **Agents**: All agents, Agent network, Evaluations, Red teaming |
| AI Gateway | LLM providers, the model chain and fallback, guardrails, cost and usage, budgets, rate limits | **AI Gateway**: LLM providers, Provider bindings, Guardrails, Guardrail rules, Policy hooks, Cost and usage, Budgets |
| Governance | Users and roles, Cedar policies, tenants, the secrets store, the audit log, incidents and compliance | **Governance**: Overview, Incidents, Compliance, Audit log. **Settings**: Access, Tenants. **Connect**: Secrets store |

Beside these platform sections, the rail lists the **solutions** a tenant has: IT service desk (Tickets, Analytics, Insights, Categories), SAP, HR and Salesforce, each with its own tabs.

> [!TIP]
> Everything the console does is a call to the same REST API under `/api/`. Anything you can click you can script, and the [API endpoints](/docs/reference/api-endpoints) page lists them all.

## Next steps

- Learn the vocabulary in [Key concepts](/docs/overview/concepts).
- Run it yourself with the [Quickstart](/docs/get-started/quickstart).
- Browse hands-on [Labs](/docs/labs).

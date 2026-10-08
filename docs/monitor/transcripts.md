---
title: Transcripts
order: 2
summary: Read an agent's conversations turn by turn, follow a turn into its trace, and control how long transcripts are kept.
outcomes: Find and open a conversation; Jump from a turn to its trace and evaluations; Set retention and use legal holds
---

## Find a conversation

1. Open the agent and its **Transcripts** tab (`GET /api/agents/{key}/transcripts`).
2. Open a conversation (`GET /api/agents/{key}/transcripts/{conv_id}`). Each turn shows the text (if the agent records it), tokens, cost and outcome.
3. Open the conversation's trace (`GET /api/transcripts/{conv_id}/trace`): one trace per request that wrote to it, the latest shown unless you pass `?trace=`, with model calls, tool calls, guardrail findings and fallback attempts in order. A conversation with recording off has no spans to show.
4. See how it was scored with `GET /api/transcripts/{conv_id}/evaluations` (each evaluator's latest run, or `?history=true` for every run).

> [!TIP]
> Save a conversation as an eval case to stop a fixed bug from coming back. See [Playground and evals](/docs/agents/playground-evals).

## What is kept

| Limit | Default | Effect |
| --- | --- | --- |
| Turns per conversation | 200 | Extra turns are counted but not kept |
| Characters per turn | 8,000 | Longer turns are cut |
| `TICKETIQ_TRANSCRIPT_MAX_CONVERSATIONS` | 5000 | Oldest conversations are dropped past this count |
| `TICKETIQ_TRANSCRIPT_RETENTION_DAYS` | 90 | Conversations older than this are dropped (a tenant's own retention window applies to its conversations) |

The agent's **recording mode** decides whether text is kept at all: `full`, `metadata` or `off`. See [Instructions and model](/docs/agents/instructions-model).

## Delete and hold

- Delete one conversation with `DELETE /api/transcripts/{conv_id}`, or many with `POST /api/transcripts/bulk-delete` (it only counts matches until you send `"dry_run": false`). Both require `governance.write`.
- A **legal hold** stops conversations from ageing out and from being deleted, until it is released. The audit log's legal hold freezes every conversation. A scoped hold covers one conversation, agent, tenant or person, and a delete it covers is refused with `409`.

## Next steps

- [Audit log](/docs/monitor/audit-log)

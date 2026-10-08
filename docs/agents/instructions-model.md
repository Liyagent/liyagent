---
title: Instructions and model
order: 3
summary: Write an agent's instructions, bind it to a provider and model, and set the run limits a managed agent works within.
outcomes: Edit instructions with template variables; Bind an agent to a provider and model; Set per-run caps for a managed agent
---

## Instructions

Instructions are the agent's standing brief, applied ahead of every governed call it makes. They live in the agent definition (`GET` / `PUT /api/agents/{key}/spec`) together with its recording mode, A2A card, telemetry and session settings.

- Markdown, up to 50,000 bytes.
- Template variables are filled in at call time: `{tenant}`, `{agent_label}` and `{date}`.
- Every save is a new version. Restore an old one with `POST /api/agents/{key}/versions/{version_id}/restore`.

| Recording mode | What transcripts keep |
| --- | --- |
| `full` | Every turn's text, within the transcript limits |
| `metadata` | Timing, tokens, cost and outcome, no text |
| `off` | Nothing |

## Tables and charts in replies

The Playground draws two things in a reply beyond prose: Markdown pipe tables, and charts. An agent writes them only when its instructions say how. In the instructions editor, **+ Tables & charts guidance** appends a paragraph that teaches the format. Edit it to suit the agent.

A chart is a fenced code block tagged `chart` that holds one JSON object:

```chart
{"type": "bar", "title": "Tickets this week", "labels": ["Mon", "Tue", "Wed"],
 "series": [{"name": "Opened", "data": [4, 7, 5]}, {"name": "Resolved", "data": [3, 6, 6]}],
 "x_label": "Day", "y_label": "Tickets"}
```

| Field | Meaning |
| --- | --- |
| `type` | `bar`, `line`, `pie` or `scatter` |
| `labels` | The categories (bar, line) or slices (pie). Not used by scatter |
| `series` | Up to 6 of `{"name": ..., "data": [...]}`. Bar and line: one value per label, `null` for a gap. Pie: exactly one series, values not negative. Scatter: `[x, y]` pairs |
| `title`, `x_label`, `y_label` | Optional captions |
| `unit` | Optional suffix shown after each value, such as `%` or ` ms` |

Limits: 60 labels for bar and line charts, 12 slices for a pie, 500 points for a scatter. The chart is drawn as SVG in the console's own colours, so it reads in the light and dark themes, and every value is also in a **Data** table under it. A block that is not a valid chart is shown as code, with the reason it was not drawn.

## Bind a model

1. On the agent's **Settings** tab, in the **Model** section, pick a provider (or **Global backend**) and a model id, and choose **Override**. A sub-agent of Liya can choose **Inherit from Liya** instead.
2. For the output token cap, reasoning effort, timeout, the two switches below and the fallback lists, open **AI Gateway › Provider bindings** and choose **Bind** on the agent's row.

Both call `PUT /api/agents/{key}`. A field you leave out keeps its stored value.

| Field | Meaning |
| --- | --- |
| `provider`, `model` | Where calls go |
| `max_tokens` | Output token cap per call |
| `effort` | Reasoning effort, for models that support it |
| `timeout` | Seconds before the call counts as timed out, which can trigger fallback |
| `strict_binding` | If the provider is deleted, switch the binding off instead of moving the agent to the global backend |
| `refuse_unpriced` | While the agent has a USD budget, refuse a model with no price, whose calls the budget could never stop |

Fallback lists live on the same binding. See [Model chain and fallback](/docs/ai-gateway/model-chain).

> [!TIP]
> To compare two models on live traffic before switching, add an arm and promote the winner with `POST /api/agents/{key}/arms/{arm}/promote`.

## Run limits for managed agents

A managed agent's runtime is on its **Settings** tab, in the **Tools** section: its MCP servers, **Run as**, the limits below and its sub-agents, saved together with **Save runtime**. It maps to `PUT /api/agents/{key}/runtime`. Check a draft with `POST /api/agents/{key}/runtime/check`.

| Field | What it limits | Default (maximum) |
| --- | --- | --- |
| Max iterations | Model calls per request (the loop always ends) | 10 (100) |
| Parallel tool calls | Independent MCP calls of one model step sent at once | Off, one at a time (4) |
| Delegation depth | Hops of registered agents a delegation may go from here | 3 (5) |
| Wall-clock deadline (s) | Total run time | 300 (3600) |
| Tool calls per run | Across the agent and its sub-agents | 50 (500) |
| Tool calls per model step | Tool calls one model step may ask for | 8 (32) |
| Delegations per run | Sub-agent calls in one run | 8 (64) |
| Identical tool calls per run | The same tool with the same arguments (stops loops) | 3 (50) |
| Token ceiling per run | Tokens across the whole run | Off (10,000,000) |
| USD ceiling per run | Cost across the whole run | Off (1,000) |

A run that reaches a limit ends with "run limit: …" naming it. Start and stop a managed agent with `POST /api/agents/{key}/start` and `POST /api/agents/{key}/stop`.

## Run as

**Run as** says whose permissions the agent's tool calls use:

| Option | What it means |
| --- | --- |
| The agent (`run_as: agent`, the default) | The agent's own permissions, whoever invokes it. Right for work with no person behind it. |
| The invoker (`run_as: invoker`) | Each run acts for the signed-in person who invoked it. Every tool call is checked for the agent **and** for that person, and refused if either may not make it. A tool that writes also needs the person to hold every permission in **Invoker must hold (for writes)** (default `tickets.write`). |

- **Per-user connectors need it.** An MCP server bound to a per-user OAuth connection sends the calling person's own token, so it can be attached only to an agent (and its sub-agents) that runs as the invoker. Switching an agent back to **The agent** detaches those servers.
- **Who counts as the invoker.** Only a person an entry point verified who has an enabled account. A call with no verified person is refused rather than run as the agent instead. Schedules, webhooks and ticket-event triggers always run as the agent.
- Switching off **The invoker**, or dropping a permission from the list, weakens a control, so the save asks for a reason.

## Writes that wait for approval

A write tool call can be held for a person to approve before it is sent. Each MCP server has a posture for its agents' writes (`agent_writes`: `allow`, `require_approval` or `deny`), with per-tool overrides:

- A server added from now on starts at **require approval** for writes.
- Some managed-connector tools (ordering from a catalogue, starting a flow) ask for approval whatever the server's default. Only a per-tool override lets them through unseen.
- A server saved before postures existed keeps allowing writes until you change it.

Held calls wait in the **Inbox** under **Approvals**. Only an agent's call is held. A person calling a tool from the console is not. See [Agent permissions](/docs/govern/permissions).

## Replies that claim a call that was not made

A model shown its earlier turns can write a reply that says an action is done when no tool call was made in this turn. The runtime checks every managed agent's final reply: if the reply carries the runtime's note of tool calls and names a call this turn did not make, the reply is replaced with a message saying nothing was changed and asking the person to try again. The runtime's note is never shown to people.

## Next steps

- [Sub-agents](/docs/agents/sub-agents)
- [Guardrails](/docs/ai-gateway/guardrails)

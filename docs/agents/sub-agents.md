---
title: Sub-agents
order: 4
summary: Let a managed agent delegate work to specialist sub-agents that spend its budget and inherit its limits.
outcomes: Add a sub-agent with its own description and instructions; Limit the tools a sub-agent can use; Explain what stops delegation loops
---

A managed agent can hand part of a task to a **sub-agent**: a new one defined on the parent, or an existing agent picked from the registry. The parent's model sees each sub-agent's description and decides when to call it.

## Prerequisites

- A managed agent (sub-agents are not available on self-managed agents).

## Add a sub-agent

1. Open the parent agent's **Settings** tab and go to the **Tools** section, where its runtime is.
2. Under **Subagents**, type a name (lowercase letters, digits and hyphens) and choose **Add subagent** to define a new one, or pick an agent and choose **Add registered agent** to reuse an existing one.
3. Fill in the fields.

   | Field | Notes |
   | --- | --- |
   | Description | What the parent reads to decide to use it. Be specific about when, not just what. |
   | Instructions | The sub-agent's own brief. New sub-agents only. |
   | Context it is given | **Task only**, **Handoff note** (the parent writes one) or **Last 6 turns of this conversation**. Passed context counts against the budget. |
   | Model override / Provider override | Optional, new sub-agents only; blank inherits the parent's. Use a cheaper model for narrow tasks. A provider override needs a model. |
   | Its MCP servers | New sub-agents only. Each tool list is held to what the parent itself may use on the same server. |

4. Choose **Save runtime**, and test from the parent's **Playground**.

> [!NOTE]
> A sub-agent defined on the parent spends the parent's budget and cannot delegate further. A registered agent used as a sub-agent runs as itself, under its own guardrails, kill switch and budget, and its cost is billed on to the parent.

## How delegation is governed

- Each delegation is checked by the Cedar `delegate` action. You can also run one directly with `POST /api/agents/{parent}/delegate/{child}`, under the parent's budget.
- A sub-agent runs as its parent runs (**Run as**), so a per-user MCP server can be ticked for it only when the parent runs as the invoker.
- A delegation that would loop back to an agent already working on the request, or exceed the parent's **Delegation depth** (default 3, at most 5), is refused.
- Cost is billed to the real parent, and every usage row carries the delegation chain, so you can see which parent a sub-agent's spend belongs to.

## Next steps

- [Playground and evals](/docs/agents/playground-evals)
- [Budgets](/docs/ai-gateway/budgets)

---
title: Build a custom sub-agent with instructions
summary: Create a managed HR agent with a narrow policy sub-agent, test delegation in the playground and see the cost land on the parent.
category: Agents
stack: [Docker]
level: Intermediate
time: 30 min
order: 4
outcomes: Create a managed agent with instructions; Add a sub-agent with its own description and model override; See delegation in the trace and in usage
---

## Prerequisites

- A running Liyagent instance with one LLM provider configured.

## Steps

1. Open **All agents** → **+ Create agent** and choose **Managed by Liyagent**. Name it `HR helper`; the agent id shown under the name becomes `hr-helper`. Under **Tags**, enter `team=hr`.
2. Pick a provider and model under **Model**, then write the **Instructions**:

   ```markdown
   You help employees of {tenant} with HR questions. Today is {date}.
   - Answer briefly and point to the policy section you used.
   - For anything about leave balances or pay, delegate to the policy specialist.
   - Never discuss another employee.
   ```

3. Choose **Create agent**, then **Start** on the agent's page.
4. On the agent's **Settings** tab, under **Subagents**, choose **Add subagent** and name it `leave-policy`:

   | Field | Value |
   | --- | --- |
   | Description | Answers questions about annual leave, sick leave and parental leave rules. Use for any question about days off. |
   | Instructions | Answer only from the leave policy. Quote the rule. If unsure, say so. |
   | Model override | A smaller, cheaper model |

5. Save. Open the **Playground** tab and ask: `How many days of parental leave can I take?`
6. Choose **Trace** on the answer: you'll see the parent's call, a `delegate` to `leave-policy`, and the child's call on the cheaper model.
7. Open the agent's **Cost & Usage** tab: the child's calls are recorded with the delegation chain that names `hr-helper` as the parent.

> [!NOTE]
> Sub-agents cannot delegate further, and a delegation past the parent's **Delegation depth** is refused.

## Next steps

- [Sub-agents](/docs/agents/sub-agents)
- [Set a budget and watch the fallback](/docs/labs/budget-fallback)

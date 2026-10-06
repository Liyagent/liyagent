---
title: Create an agent
order: 2
summary: Create a managed agent from the Fleet page, give it an identity and first instructions, and start it.
outcomes: Create a managed agent with an id, display name and tags; Know which fields can change later and which cannot; Create the same agent with the API
---

## Prerequisites

- The **admin** or **owner** role, or a custom role that grants agent creation.
- At least one LLM provider, if the agent will call a model. See [LLM providers](/docs/ai-gateway/providers).

## Steps

1. Open **Agents › All agents** and choose **+ Create agent** (or go to `/agents/create`).
2. Choose **Managed by Liyagent**. The type is fixed once the agent is created.
3. Fill in the form. Managed agents have six sections:

   | Section | Notes |
   | --- | --- |
   | 01 Identity | **Name** and **Description**. The **Agent id** is made from the name (lowercase letters, digits and hyphens; a taken id gets a number). It is the agent's permanent key: budgets, policies and the audit log address it, and it cannot be changed later. |
   | 02 Model | The provider and model it reasons with, from this instance's connected providers, or the instance default backend. |
   | 03 Instructions | Its system prompt, in Markdown. Start from a template or write your own; edit it later on the agent's **Settings** tab. |
   | 04 Tools | The MCP servers it may call. You can attach more later. |
   | 05 Access | Who may use it: the access policy created with it. |
   | 06 Tags | Under **Advanced**: `key=value`, comma-separated. Usage and cost reports can be broken down by tag. An instance can require some tags. |

4. Choose **Create agent**. One submit creates the agent, its model binding, its MCP servers and its access policy; if a step fails, the agent is deleted again so nothing is left half-made.
5. The agent opens on its own page. Start it from there, and refine it on **Settings** (see [Instructions and model](/docs/agents/instructions-model)).

> [!NOTE]
> Choose **Self-managed** instead when the agent's code runs on your infrastructure. It then gets a credential and calls the gateway; see [Set up your agent](/docs/get-started/set-up-your-agent).

## With the API

```bash
curl -X PUT https://<host>/api/gateway/agents/hr-helper \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"label":"HR helper","about":"Answers HR policy questions",
       "runtime":"managed","prompt":"You answer questions about the HR handbook.",
       "tags":["team=hr"]}'
```

`tags` is a list of `key=value` strings. Bind its model with `PUT /api/agents/hr-helper` and attach tools with `PUT /api/agents/hr-helper/runtime`. Other agent routes: `GET /api/gateway/agents`, `GET`, `PATCH` and `DELETE /api/gateway/agents/{agent_id}`.

## Next steps

- [Instructions and model](/docs/agents/instructions-model)
- [Sub-agents](/docs/agents/sub-agents)
- [Playground and evals](/docs/agents/playground-evals)

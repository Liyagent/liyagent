---
title: Agent permissions
order: 3
summary: See who may act on an agent and what the agent itself may do, and check a single decision before you rely on it.
outcomes: Read an agent's Permissions tab; Check whether a specific call would be allowed; Record an agent's owner and risk tier
---

## The Permissions tab

Open an agent's **Permissions** tab (`GET /api/agents/{key}/permissions`). It has two halves:

| Section | Answers |
| --- | --- |
| Granted access | Policies that grant people or groups direct access to this agent (roles still decide whether someone may touch agents at all) |
| Access policies | What this agent may do as its own principal: the models it may call, the tools it may use |

Both list the Cedar policies on **Access** that name this agent. **Apply least-privilege defaults** creates the recommended policies for the agent's job. A system policy caps every agent whatever these say.

## Check a decision

Before relying on a rule, ask the policy engine directly:

```bash
curl -X POST https://<host>/api/permissions/check -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"principal":{"kind":"Agent","id":"hr-helper"},
       "checks":[{"entity":"agent","verb":"update","name":"hr-helper"}]}'
```

Leave out `principal` to ask about yourself; asking about another principal (`User`, `Agent` or `Client`) needs `access.read`. Each check names an entity, a verb and optionally a resource name; the answer says allowed or denied for each, and a denial names what denied it.

`GET /api/permissions/schema` lists the entity types and actions you can use.

## Registry

The **Registry** tab records accountability for the agent (`GET /api/agents/{key}/registry`):

| Field | Notes |
| --- | --- |
| Owners, responders | Who is accountable and who is paged |
| Risk tier | `minimal`, `limited`, `high` or `prohibited` |
| Intended purpose, out of scope | What it is for and not for |
| Known issues | Limitations users should know about |

Hand an agent to a new owner with `POST /api/agents/{key}/registry/transfer`; nothing changes hands until they accept it with `POST /api/agents/{key}/registry/transfer/accept`.

## Approvals for tool calls

Separately from Cedar, each MCP server sets what an agent's call of a tool gets: **Allow**, **Require approval** (held until a person approves) or **Deny**.

- On a server added from now on, write tools start at **Require approval**; read tools are allowed. A server saved before postures existed keeps allowing writes until you change it.
- Some managed tools, such as ordering a catalog item or starting a flow, are held for approval whatever the server's default, unless a per-tool override says otherwise.
- A per-tool override wins, and rules on the arguments can escalate a call to approval or deny it; rules only tighten.
- Only an agent's calls are held, never a person's own. Approving needs the `agents.approve` permission; each approval is single-use and expires (`TICKETIQ_AGENT_APPROVAL_TTL_S`). Requests are listed at `GET /api/approvals`.

## Next steps

- [Access](/docs/govern/access)

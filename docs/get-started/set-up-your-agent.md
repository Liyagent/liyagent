---
title: Set up your agent
order: 4
summary: Bring an agent you already run under Liyagent governance by registering it as self-managed and routing its model calls through the gateway.
outcomes: Register an existing agent as self-managed; Issue it a gateway credential; Apply a budget, a guardrail and a policy to it
---

## Prerequisites

- A running Liyagent instance and an account with the **admin** or **owner** role.
- An agent that uses an OpenAI-compatible client (most frameworks do).

## Steps

1. Open **Agents › All agents**, choose **+ Create agent**, then **Self-managed**.
2. Fill in the form:

   | Section | Notes |
   | --- | --- |
   | 01 Identity | **Name** and **Description**. The **Agent id** is made from the name (lowercase letters, digits and hyphens) and cannot be changed later. |
   | 02 Access | Who may use it: the access policy created with it. |
   | 03 Tags | Under **Advanced**: `key=value` pairs, comma-separated, used for cost chargeback, for example `team=hr,env=prod`. |

3. Choose **Create and issue credentials**. The agent is registered (`PUT /api/gateway/agents/{agent_id}`) and a credential is issued (`POST /api/agents/{agent_id}/credentials`). The page shows its `client_id`, `client_secret`, the token URL and the AI Gateway base URL. **Copy the secret now: it is shown once.** Store it in your agent's secret manager. Credentials last 90 days by default. Issue more, or revoke one, on the agent's **Credentials** view (**Create credential**).
4. In your agent, get an access token with the OAuth client-credentials grant at `POST /api/gateway/oauth/token`. A token lasts one hour. Get a new one when it expires.
5. Point the agent's OpenAI client at the gateway: base URL `https://<your-host>/api/gateway/v1`, API key the access token. Chat completions go to `POST /api/gateway/v1/chat/completions`.

   ```python
   import httpx
   from openai import OpenAI

   HOST = "https://ticketiq.example.com"
   tok = httpx.post(f"{HOST}/api/gateway/oauth/token", data={
       "grant_type": "client_credentials",
       "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}).json()["access_token"]
   client = OpenAI(base_url=f"{HOST}/api/gateway/v1", api_key=tok)
   bound = client.models.list().data[0].id   # the model this agent is bound to
   client.chat.completions.create(model=bound, messages=[{"role": "user", "content": "hello"}])
   ```
6. Make one call and open the agent's **Cost & Usage** tab: the call is there with tokens and cost.

> [!NOTE]
> A long-lived static token also exists for older integrations: `POST /api/gateway/agents/{agent_id}/token` mints one (issuing again replaces it), and `DELETE` revokes it. Prefer the client-credentials flow above.

## Put controls around it

- **Budget:** add a scoped budget with scope kind *agent* on **Budgets**. See [Budgets](/docs/ai-gateway/budgets).
- **Guardrail:** bind a guardrail set to the agent. See [Create a guardrail](/docs/ai-gateway/create-guardrail).
- **Policy:** restrict what it may call with a Cedar policy or the **Read only** / **Sandboxed** templates. See [Access](/docs/govern/access).

> [!TIP]
> You can switch an agent between managed and self-managed later with `POST /api/gateway/agents/{agent_id}/convert`.

## Next steps

- [Agent permissions](/docs/govern/permissions)
- [Audit log](/docs/monitor/audit-log)

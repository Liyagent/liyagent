---
title: Add a free OpenRouter model to the chain
summary: Add OpenRouter as an OpenAI-compatible provider and use a free model as a fallback that is skipped automatically once its daily quota is used.
category: Governance
stack: [Docker]
level: Beginner
time: 20 min
order: 5
outcomes: Add an OpenAI-compatible provider pointed at OpenRouter; Add a free model as a fallback entry; See a dead model skipped until its reset
---

## Prerequisites

- A running Liyagent instance and an agent with a primary model binding.
- An OpenRouter account and API key.

## Steps

1. Open **LLM providers** → **+ Add provider** and pick **OpenRouter** under **OpenAI-compatible presets**. The base URL is filled in as `https://openrouter.ai/api/v1`.

   | Field | Value |
   | --- | --- |
   | Display name | `OpenRouter` |
   | Credential | **API key**, pasted once (it is stored encrypted in the Secrets store), or an existing key reference |
   | Models | a model id ending in `:free`, for example `meta-llama/llama-3.3-70b-instruct:free` |

2. Choose **Test connection**, then **Create provider**.
3. Open **Provider bindings** and edit your agent's binding. Under **Fallbacks** → **When the provider does not answer**, choose **+ Add fallback** and pick the free model on OpenRouter.
4. Check **Move down the first list on**: the defaults already cover 429, 5xx, timeouts, connection errors and an open circuit. Save.
5. Force a fallback: temporarily disable the primary provider (`POST /api/llm/providers/{name}/disable`), then send a message in the **Playground**. The trace shows two attempts, the second on OpenRouter.
6. Re-enable the primary provider (`POST /api/llm/providers/{name}/enable`).

> [!NOTE]
> When a free model's per-day quota runs out, OpenRouter says so in its error. Liyagent marks the model dead and skips it until the reset time in the error, instead of paying for the same failure on every call.

## Next steps

- [Model chain and fallback](/docs/ai-gateway/model-chain)

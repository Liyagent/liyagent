---
title: LLM providers
order: 2
preview: true
summary: Add Amazon Bedrock, Anthropic, Google Gemini, Vertex AI or any OpenAI-compatible endpoint, test it, and watch its health.
outcomes: Add and test a provider before saving it; Keep its key in the secrets store; Read provider health and the circuit state
---

> [!PREVIEW]
> The console has two provider pages. **Provider bindings** holds the providers agents bind to (the `/api/llm/providers` API) and is what this page describes. **LLM providers** is a newer page for providers routed through the gateway (`/api/llm-gateway/providers`); it offers Anthropic, AWS Bedrock, Google AI, OpenAI and OpenAI-compatible, but not Vertex AI yet.

## Provider types

| Type | Use for |
| --- | --- |
| Amazon Bedrock | Claude and other models in your AWS account |
| Anthropic | Anthropic's API directly |
| Google Gemini | Gemini API keys |
| Google Vertex AI | Gemini and partner models in your GCP project |
| OpenAI-compatible | OpenAI, Azure OpenAI, OpenRouter, vLLM, llama.cpp, Ollama: anything that speaks the OpenAI API |

## Add a provider

1. Open **Provider bindings** and choose **+ Add provider**. Pick a type.
2. Fill in the form.

   | Field | Notes |
   | --- | --- |
   | Base URL | For OpenAI-compatible providers, for example `https://openrouter.ai/api/v1` |
   | Endpoint override (optional) | A regional or private endpoint |
   | Credential | A key, or `secret://<label>` from the secrets store |
   | Default model | Used when an agent binds to the provider without naming a model |
   | Data handling | Record the provider's data terms, for example no training on inputs |
   | Enabled | Off keeps it configured but unused |

3. Test before saving: **Test connection** calls `POST /api/llm/providers/test`. **Create provider** saves it. Once saved, the provider shows a **Gateway URL**: set it as an OpenAI SDK's base URL, with an agent token as the key, to call the provider through the gateway.
4. List its models (`GET /api/llm/providers/{name}/models`) and bind agents to them.

> [!TIP]
> `POST /api/llm/providers/discover` lists the models a provider would serve from the details in the form, before it is saved.

## Health and circuits

The providers table shows **Status**, **Default model**, **Health** and **Used by**. A provider's details add its **Circuit**, and its **Leaderboard** tab ranks the callers that use it and the models they reach for.

- Health comes from scheduled probes (`GET /api/llm/provider-health`; run one now with `POST /api/llm/providers/{name}/health/probe`). A failed probe opens the provider's circuit.
- Each backend has a circuit breaker: closed, open, or half-open with a single probe. Each breaker's state is at `GET /api/llm/breakers`.

## Next steps

- [Model chain and fallback](/docs/ai-gateway/model-chain)
- [Lab: Add a free OpenRouter model to the chain](/docs/labs/openrouter-free-model)

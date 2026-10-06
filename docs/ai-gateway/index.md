---
title: AI Gateway & LLM providers
order: 1
summary: One governed path for every model call: providers, the model chain and fallback, guardrails, budgets and metering.
---

Every model call in Liyagent, from a built-in Liya agent, a managed agent or a self-managed agent calling `/api/gateway/v1/chat/completions`, goes through the same steps:

<div class="diagram"><svg viewBox="0 0 760 120" role="img" aria-label="Gateway steps: authorize, limits and budget, input guardrails, model with fallback, output guardrails, meter and audit">
<defs><marker id="gw-a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="d-arrow" d="M0 0L10 5L0 10z"/></marker></defs>
<rect class="d-box" x="4" y="30" width="108" height="56" rx="8"/><text x="58" y="56" text-anchor="middle">Authorize</text><text class="d-sub" x="58" y="74" text-anchor="middle">Cedar</text>
<rect class="d-box" x="130" y="30" width="108" height="56" rx="8"/><text x="184" y="56" text-anchor="middle">Limits</text><text class="d-sub" x="184" y="74" text-anchor="middle">rate + budget</text>
<rect class="d-box" x="256" y="30" width="108" height="56" rx="8"/><text x="310" y="56" text-anchor="middle">Guardrails</text><text class="d-sub" x="310" y="74" text-anchor="middle">input</text>
<rect class="d-hot" x="382" y="30" width="118" height="56" rx="8"/><text x="441" y="56" text-anchor="middle">Model</text><text class="d-sub" x="441" y="74" text-anchor="middle">chain + fallback</text>
<rect class="d-box" x="518" y="30" width="108" height="56" rx="8"/><text x="572" y="56" text-anchor="middle">Guardrails</text><text class="d-sub" x="572" y="74" text-anchor="middle">output</text>
<rect class="d-box" x="644" y="30" width="110" height="56" rx="8"/><text x="699" y="56" text-anchor="middle">Meter</text><text class="d-sub" x="699" y="74" text-anchor="middle">usage + audit</text>
<path class="d-line" d="M112 58H128" marker-end="url(#gw-a)"/><path class="d-line" d="M238 58H254" marker-end="url(#gw-a)"/><path class="d-line" d="M364 58H380" marker-end="url(#gw-a)"/><path class="d-line" d="M500 58H516" marker-end="url(#gw-a)"/><path class="d-line" d="M626 58H642" marker-end="url(#gw-a)"/>
</svg></div>

A refusal at any step is recorded in the audit log with the reason, and nothing after it runs. The pages below cover each step you configure.

## Two wire formats, one path

| Clients that speak | Point them at | Authenticate with |
| --- | --- | --- |
| OpenAI chat completions (the OpenAI SDKs, most frameworks) | `https://<instance>/api/gateway/v1` | the agent's gateway token as the API key |
| Anthropic Messages (Claude Code, the Anthropic SDKs) | `https://<instance>/api/gateway/anthropic` | the agent's gateway token, as `ANTHROPIC_AUTH_TOKEN` (a bearer) or `ANTHROPIC_API_KEY` |

The Anthropic endpoint translates each Messages request into the same governed call, so every step above applies and every call is one `gateway.call` row in the audit log. It carries text, images, tool use and tool results, client tools and `tool_choice`, and streams Anthropic's events when asked. The model that answers is the agent's binding, whatever model the client names, and the response says which one it was.

What it does not carry:

- **Anthropic's server-side tools** (web search, code execution) run on Anthropic's servers, which a governed call never reaches. They are left out of the request and named in the `X-TicketIQ-Dropped-Tools` response header.
- **Thinking blocks** in the conversation are dropped; only the model that wrote them can read them back. Sampling settings (temperature, stop sequences, the thinking budget) are the binding's to decide.
- **Any other block** (a PDF document, a server tool's result) is refused with a `422`, rather than dropped without a guardrail reading it.
- **count_tokens** answers an estimate, about four characters a token: the agent may run on a model whose tokenizer the gateway cannot run.

To start Claude Code this way from a terminal, see [`liya run claude`](/docs/cli#run-claude-code-through-the-gateway).

---
title: Glossary
order: 5
summary: Short definitions of the terms used across Liyagent.
---

| Term | Meaning |
| --- | --- |
| A2A | Agent-to-agent protocol. Liyagent can publish an agent card and call remote agents. |
| Binding (model) | The provider, model and fallback lists an agent calls. |
| Binding (guardrail) | Which guardrail set applies to which agent. |
| Breaker | Per-backend circuit breaker: closed, open or half-open. |
| Cedar | The policy language Liyagent uses for authorization. |
| Deflection | Answering a request without a ticket reaching a person. |
| Dead model | A model skipped until its reset time after the provider says it is gone or out of quota. |
| Engine | How a decision is made: rules, rules plus model, or model. |
| Evidence bundle | A signed export of the hash-chained audit log that anyone can verify offline with the instance's published audit signing key. |
| Known issue | An open ticket that later duplicate reports are folded into. |
| Liya | Liyagent's agent family, and the agent people talk to. |
| Managed agent | An agent Liyagent runs: instructions, tools, sub-agents and limits in the console. |
| MCP | Model Context Protocol, how agents get tools. |
| Run as | Whose permissions a managed agent's tool calls use: the agent's own, or the invoker's as well. |
| Self-managed agent | An agent running elsewhere that calls the gateway with its own credential. |
| Semantic cache | Reuse of a verified earlier answer for a question that means the same thing. |
| Sensitivity label | public, internal, confidential or restricted; limits where an item may be retrieved. |
| Sub-agent | A specialist a managed agent can delegate to; one defined on the parent spends the parent's budget. |
| Taxonomy | A tenant's categories, default IT or learned from its tickets. |
| Tenant | A separated slice of one instance with its own data and settings. |
| Trigger | An inbound channel bound to one agent. |
| Write posture | Whether an agent's write tool call on an MCP server is allowed, held for approval or denied. |

---
title: Build agents
order: 1
summary: Create managed agents, give them instructions, a model, tools and sub-agents, test them and wire them to channels.
---

An agent in Liyagent is anything that makes model calls through the gateway: the built-in Liya agents, **managed** agents that Liyagent runs for you, and **self-managed** agents that run elsewhere and call the gateway. They are all listed under **Agents › All agents** (`/fleet`), and each has its own page at `/agent?id=<key>` with six tabs:

| Tab | What it holds |
| --- | --- |
| Settings | The definition: Instructions, Engine, Model, Tools (a managed agent's runtime, run limits and sub-agents), Subagents, Context & memory, Posture, Workflows, Identity & tags, Agent card, Evaluations and Kill switch. Its views also include Context, Posture, Registry, History and Changes, plus Workflows (managed) or Credentials and Telemetry (self-managed) |
| Triggers | The channels that start it |
| Playground | Try it through the governed path |
| Cost & Usage | Its calls, tokens and spend |
| Transcripts | Its conversations, with the Traces and Sessions views |
| Permissions | Who may use it and what it may reach |

A link can open a view directly with `?tab=`, for example `/agent?id=copilot&tab=traces`.

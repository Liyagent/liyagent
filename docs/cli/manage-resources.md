---
title: Manage resources
order: 3
summary: List, inspect, create and test agents, tickets, providers, guardrails, secrets, policies and budgets from the terminal.
outcomes: Find and inspect any resource; Chat with and evaluate an agent; Search the audit log from the terminal
---

## Agents

```bash
liya agents list
liya agents get hr-helper
liya agents create hr-helper --from-blueprint triage-assistant --tag team=hr
liya agents chat hr-helper "How many days of leave do I have?"
liya agents eval hr-helper --dataset hr-faq        # exits 1 on a failure or regression
```

`liya agents create` installs a blueprint (an unknown name lists the available ones); create other agents in the console or with `PUT /api/gateway/agents/{agent_id}`. `liya agents update`, `delete`, `pause` and `resume` work on existing agents.

## Who may use an agent, and what it may reach

A new agent is not locked down. Cedar governs a resource only once some policy names it, so until then:

- **People** reach the agent through their roles.
- **The agent itself** can call the LLM provider it is bound to and the tools of every MCP server attached to it. Its write calls still meet each server's write posture: a server added now holds them for approval until you change it.

`liya agents create` says this when it creates the agent. To decide who may use it, bind one of the built-in templates. A template is what a **person** may do with the agent:

| Template | People it names may |
| --- | --- |
| `readonly` | Read the agent: transcripts, cost, the validation log |
| `sandboxed` | Read it and run it (playground, triggers) |
| `standard` | Run and reconfigure it, and use it as a subagent; not its kill switch |
| `full` | Everything, the kill switch included |

```bash
liya policies create ops-run-hr --agent hr-helper --template sandboxed --principal group:ops
liya policies create admin-owns-hr --agent hr-helper --template full --principal user:admin
```

`--principal` is `any` (the default), `user:NAME`, `group:NAME` or `role:NAME`. The moment a policy names the agent it is governed: people without a permit lose what their roles gave them.

The agent's **own** tool and model calls are a separate decision, with the agent as the principal. `--agent-tools` writes them as the template implies:

| Template | The agent itself may |
| --- | --- |
| `readonly`, `sandboxed` | Call none of its attached MCP servers' tools. It answers from its model alone |
| `standard` | Call its attached servers' tools |
| `full` | Call those tools and its bound LLM provider |

A policy that names an MCP server or provider governs it for **every** agent, so a permit for one agent takes that server from any other agent that has no permit of its own. Each policy is analysed before it is written. If the analysis finds that, or finds that no one would be left who may configure or contain the agent, nothing is created and the command exits `2`. Pass `--yes` to create it anyway, or `--dry-run` to see the policies and their impact first.

## Everything else

| Resource | Examples |
| --- | --- |
| Tickets | `liya tickets list --status open`, `liya tickets get TIQ-5A03DE`, `liya tickets create`, `comment`, `close` |
| Providers | `liya providers list`, `liya providers test openrouter` |
| Guardrails | `liya guardrails list`, `liya guardrails test "my SSN is ..." --agent copilot` (exit 5 if it would be blocked) |
| Secrets | `liya secrets list`, `liya secrets set jira-api-token` (reads the value from stdin) |
| Policies | `liya policies create ops-run-hr --agent hr-helper --template sandboxed --principal group:ops`, `liya policies apply -f policies.yaml` |
| Budgets | `liya budgets list`, `liya budgets set --agent hr-helper --limit 50 --period month` |
| Audit | `liya audit search actor=alice outcome=denied --since 24h`, `liya audit verify` |

## Health

```bash
liya status    # gateway, model chain and connector health
liya doctor    # Python and modules, credentials-file permissions, reachability, your login, client and server versions
```

> [!NOTE]
> `liya secrets set` never takes the value as an argument, so it doesn't end up in shell history.

## Next steps

- [Format output](/docs/cli/output-format)
- [Command reference](/docs/cli/reference)

---
title: liya command summary
nav_title: Command summary
order: 3
summary: Every liya command and its main options on one page: global flags, environments, agents, tickets, models, guardrails and more.
---

`liya` is installed from the TicketIQ repository (see [Install liya](/docs/reference/install-liya)). For every flag, see the [generated command reference](/docs/cli/reference).

## Global options

| Option | Meaning |
| --- | --- |
| `-o table\|json\|yaml` | Output format: `table` by default, or `LIYA_OUTPUT` |
| `--env <name>` / `--url <url>` | Run against another environment or instance |
| `--timeout <s>` | HTTP timeout |
| `--no-color` | No colour (also `NO_COLOR`) |
| `-v`, `--verbose` | Log each request's method, URL, status and latency to stderr |
| `-h`, `--help` | Help for any command |

## Commands

| Command | Does |
| --- | --- |
| `liya auth login` / `logout` / `status` | Sign in, sign out, show who you are |
| `liya env list` / `use <name>` / `add <name> --url <url>` / `remove` | Manage environments |
| `liya agents list` / `get` / `create --from-blueprint` / `update` / `delete` / `pause` / `resume` / `chat` / `eval` | Agents |
| `liya tickets list` / `get` / `create` / `comment` / `close` | Tickets |
| `liya triggers list` / `create` / `delete` | Triggers |
| `liya providers list` / `add` / `test` | LLM providers |
| `liya models list` | The model catalogue |
| `liya guardrails list` / `test` | Guardrails |
| `liya secrets list` / `set` / `delete` | Secrets (values from stdin or a hidden prompt) |
| `liya policies list` / `get` / `create` / `apply -f <file>` | Cedar policies |
| `liya audit search` / `verify` | The audit log |
| `liya budgets list` / `set` | Budgets |
| `liya tenant solutions` / `adopt-legacy` | A tenant's solutions |
| `liya connectors list` / `test` | Connectors |
| `liya kb search` | The knowledge base |
| `liya status` | Gateway, model chain and connector health |
| `liya doctor` | Diagnose the CLI's setup and connection |
| `liya apply -f <path>` / `liya export -o <dir>` | GitOps: apply files, export live resources |
| `liya run claude` | Start Claude Code with its model calls through the AI gateway |
| `liya version` / `completion` | Versions, and a shell completion script |

## tiq verbs through liya

`liya` forwards these `tiq` verbs unchanged, using the current environment and credential. The `tiq` command itself still works too.

| Command | Does |
| --- | --- |
| `liya ask <agent> "<question>"` | Run one agent, print the reply |
| `liya usage --days 30` | Spend and tokens |
| `liya policy get <name>` | One policy |
| `liya network` | Which agent calls which provider |
| `liya trigger fire <token> "<text>"` | Exercise an inbound endpoint |
| `liya eval run --dataset <d> --fail-on-regression` | CI gate on evals |
| `liya plan -f`, `liya replay`, `liya delete -f` | Lifecycle verbs for pipelines |

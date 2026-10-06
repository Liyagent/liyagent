---
title: liya CLI
order: 1
summary: Install liya, the Liyagent command line, and run your first commands.
---

`liya` is the official command line for Liyagent and TicketIQ. It covers agents, tickets, triggers, LLM providers and models, guardrails, secrets, Cedar policies, the audit log, budgets, connectors and the knowledge base, and it can export and apply the whole configuration as YAML.

Every command calls the same REST API the web console uses, so anything you do with `liya` you can also see and undo in the console. When a server is too old to have an endpoint, `liya` says **not supported by this server version** rather than failing with a stack trace.

## Install

From a checkout:

```bash
pip install .            # installs the `liya` (and legacy `tiq`) console scripts
liya --version
```

Without installing, run it straight from the repository with `./liya ...` or `python -m ticketiq.cli ...`.

It needs Python 3.10 or later, `httpx` and `pyyaml`, and nothing else.

## First commands

```bash
liya env add dev --url http://127.0.0.1:8787 --use   # a server started with run.py (or: liya env use demo)
liya auth login                       # asks for an API token, input hidden
liya status                           # command-center summary: gateway, model chain, connectors
liya agents list
liya agents chat copilot "VPN drops hourly"
liya audit search outcome=denied --since 24h
```

> [!NOTE]
> The built-in `local` environment points at `http://127.0.0.1:8787`, the server's default port. For a server on another port, add your own environment, as above, or pass `--url`.

## Output

Commands print a table by default. Pass `-o json` or `-o yaml` to any command to get the server's full payload in a form you can pipe:

```bash
liya agents list -o json | jq -r '.agents[] | select(.llm) | .key'
liya tickets get TIQ-5A03DE -o yaml
```

Tables go to stdout and hints go to stderr, so a pipe only ever carries data. Colour is used only on a terminal. It is turned off by `NO_COLOR`, by `--no-color`, or when output is redirected. You can set a default format with `LIYA_OUTPUT=json`.

## Exit codes

Each kind of failure has its own code, so a script can tell "fix the input" from "fix the token" from "it is gone" without reading the message. The message itself is always printed on stderr, with the server's reason.

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Any other error: the server unreachable, a conflict, a server error |
| `2` | Invalid input: a usage error, a value the CLI cannot read (`--since yesterday`), a request the server refused as invalid (400, 422), a file that does not parse |
| `3` | Authentication or authorization: not logged in, a token or service account refused (401), a permission missing (403) |
| `4` | Not found: the agent, ticket, environment or other thing you named does not exist |
| `5` | A deliberate "no": `apply --dry-run` found pending changes, `guardrails test` would block, `agents chat` got no reply (budget, kill switch or no model), `policies create --dry-run` |

> [!NOTE]
> Before this release a pending `apply --dry-run` exited `2`. It now exits `5`, and `2` means the input was invalid, so a pipeline can never read a broken manifest as "changes pending".

## Seeing each request

`--verbose` (or `-v`, or `LIYA_VERBOSE=1`) prints one line per HTTP request on stderr: the method, the URL, the status and how long it took.

```text
liya: GET https://ticketiq.example.com/api/agents -> 200 (84 ms)
```

Headers are never printed, so neither is your token. A query value under a name that looks like a credential (`access_token`, `client_secret`, …) is shown as `***`, as are credentials written into the URL itself.

## Run Claude Code through the gateway

`liya run claude` starts Claude Code with every model call going through the AI gateway as one agent's governed call: its kill switch, Cedar policies, guardrails, budget and rate limits apply, and each call is a `gateway.call` row in the audit log.

```bash
export LIYA_GATEWAY_TOKEN=…            # the agent's gateway token, or:
liya run claude --agent coder          # mint one (replaces coder's current token; asks first)
liya run claude -- -p "explain this repo"   # anything after -- goes to Claude Code
liya run claude --dry-run              # show what would run, the token masked
```

It sets `ANTHROPIC_BASE_URL` to the instance's Anthropic endpoint (`/api/gateway/anthropic`) and `ANTHROPIC_AUTH_TOKEN` to the token. Claude Code's exit status is `liya`'s.

Claude Code's own settings apply over the environment it is started with, so a setting that would send calls somewhere else stops the launch before it starts (exit `2`), naming the file:

- `CLAUDE_CODE_USE_VERTEX`, `CLAUDE_CODE_USE_BEDROCK` or `CLAUDE_CODE_USE_FOUNDRY` in `~/.claude/settings.json`, the project's `.claude/settings.json` or `.claude/settings.local.json`, or the managed settings file — unless that file's own `ANTHROPIC_VERTEX_BASE_URL` (or the Bedrock or Foundry one) points at this instance's gateway;
- an `ANTHROPIC_BASE_URL` of its own in one of those files.

The same variables set only in your shell are not a refusal: Claude Code is started without them, and `liya` says which it left out. An API key or `apiKeyHelper` in a settings file is a warning: Claude Code would send it in place of the agent's token, and the gateway would refuse it.

## Diagnostics

`liya doctor` checks your Python version and dependencies, the permissions on the credentials file, reachability and latency, whether your credential is accepted, and whether the client and server versions match. It exits `1` if any check fails.

## Coming from `tiq`

`liya` absorbs the earlier `tiq` command line. The `tiq` verbs that `liya` does not redefine (`ask`, `usage`, `plan`, `policy`, `network`, `trigger`, `eval`, `agent`, `replay`, `delete`) are forwarded to it unchanged, using your current `liya` environment and credential. The `./tiq` wrapper and `python -m ticketiq.cli plan -f bundle.json` both still work. See [Command reference](reference.md) for everything else.

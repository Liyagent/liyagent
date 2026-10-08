<p align="center">
  <a href="https://liyagent.com"><img src="https://liyagent.com/img/liyagent-logo.png" width="88" alt="Liyagent"></a>
</p>

<h1 align="center">Liyagent</h1>

<p align="center">
  <strong>Self-hosted AI agents that ask before they act.</strong>
</p>

<p align="center">
  <a href="https://liyagent.com">Website</a> &nbsp;|&nbsp;
  <a href="https://liyagent.com/try">Live demo</a> &nbsp;|&nbsp;
  <a href="https://liyagent.com/docs">Documentation</a> &nbsp;|&nbsp;
  <a href="https://liyagent.com/docs/cli">CLI guide</a> &nbsp;|&nbsp;
  <a href="SECURITY.md">Security</a>
</p>

<br>

## Overview

[Liyagent](https://liyagent.com) runs AI agents inside the business systems a company already uses: IT service desks, HR, SAP, Salesforce, Dynamics 365 and finance.

Every agent is governed by the same controls:

- **Identity.** An agent acts as the person who asked, with that person's permissions.
- **Approval.** Any action that changes data waits for a person to approve it.
- **Spend.** Each agent has a budget that it cannot exceed.
- **Evidence.** Every action is recorded in a hash-chained audit log. Exports are signed, so anyone can verify them independently.

Liyagent runs on your own infrastructure with the AI model of your choice.

This repository contains the open-source components of Liyagent, released under the Apache License 2.0. The Liyagent platform itself is commercial software. You can try it without signing up at [liyagent.com/try](https://liyagent.com/try), or contact us at sales@liyagent.com.

<br>

## Contents

| Path | Description |
| --- | --- |
| [`liya/`](liya) | The `liya` command line for a Liyagent instance. It manages agents, tickets, triggers, models, guardrails, secrets, policies, budgets, connectors and the audit log. |
| [`tools/verify_audit_bundle.py`](tools/verify_audit_bundle.py) | A standalone verifier for audit evidence bundles. It checks the Ed25519 signature, the hash chain and every file hash, without access to the instance. |
| [`examples/liyagent_guard.py`](examples/liyagent_guard.py) | Applies Liyagent's policies, guardrails and approvals to the tools of your own agent framework. |
| [`examples/ci/liyagent.yml`](examples/ci/liyagent.yml) | A GitHub Actions workflow for managing agents as code. |
| [`docs/`](docs) | The Liyagent documentation and labs, in Markdown. |

<br>

## Installation

The command line requires Python 3.10 or later.

```bash
pipx install "git+https://github.com/liyagent/liyagent.git"
liya --version
```

<br>

## Getting started

Connect to an instance and sign in:

```bash
liya env add prod --url https://liyagent.example.com --use
liya auth login
```

Check the instance and its agents:

```bash
liya status
liya agents list
```

Send a message to an agent:

```bash
liya agents chat <agent-id> "Summarise this week's open incidents."
```

Review the actions that were refused in the last day:

```bash
liya audit search outcome=denied --since 24h
```

Results are shown as a table by default. Add `-o json` or `-o yaml` for use in scripts. The full command reference is at [liyagent.com/docs/cli/reference](https://liyagent.com/docs/cli/reference).

<br>

## Agents as code

Export the configuration of an instance, keep it in version control and apply changes in a controlled way.

```bash
liya export -o ./liyagent
liya apply -f ./liyagent --dry-run
liya apply -f ./liyagent --reason "Raise the HR agent budget for quarter end"
```

| Command | Behaviour |
| --- | --- |
| `liya export` | Writes agents, providers, guardrails, policies and triggers as YAML. Secrets are never exported. |
| `liya apply --dry-run` | Shows the changes. Exits with code 5 when changes are pending. |
| `liya apply --reason` | Applies the changes. The reason is recorded in the audit log for any change that weakens a control. |

Before a change is released, run the agent's evaluation set against its approved baseline:

```bash
liya agents eval service-desk --baseline pinned
```

The command exits with code 0 when the evaluation passes and 1 when it fails or regresses. The [CI example](examples/ci/liyagent.yml) runs these steps in GitHub Actions.

<br>

## Verifying audit evidence

A Liyagent instance can export its audit log as a signed evidence bundle. Anyone can verify a bundle without trusting the server that produced it.

With the command line:

```bash
liya audit verify audit-evidence-2026-10-06.zip --audit-keys keys.json
```

With the standalone verifier, which needs only the `cryptography` package:

```bash
pip install cryptography
curl -s https://liyagent.example.com/.well-known/liyagent-audit-key.json -o keys.json
python tools/verify_audit_bundle.py audit-evidence-2026-10-06.zip --keys keys.json
```

| Exit code | Result |
| --- | --- |
| `0` | Verified. The signature, the hash chain and every file hash are valid. |
| `1` | The bundle could not be read. |
| `2` | A check failed. The output describes the finding. |
| `3` | The bundle is intact, but no key was provided to verify the signer. |

See [Audit log](https://liyagent.com/docs/monitor/audit-log) for how the log and its bundles are built.

<br>

## Governing your own agents

[`liyagent_guard.py`](examples/liyagent_guard.py) lets an agent built with any framework use Liyagent for its decisions. Before each tool call, it asks Liyagent whether the call is allowed.

```python
import os
from liyagent_guard import Guard, Denied, PendingApproval

guard = Guard("https://liyagent.example.com", token=os.environ["LIYAGENT_AGENT_TOKEN"])

@guard.tool(writes=True)
def refund(order: str, amount: int) -> str:
    ...

try:
    refund("SO-1042", 120)
except PendingApproval as pending:
    print("Waiting for approval:", pending.approval_id)
except Denied as denied:
    print("Refused:", denied.decision)
```

If Liyagent cannot be reached, the call is not made.

<br>

## Documentation

- [What is an agentic AI platform?](https://liyagent.com/docs/overview/agentic-ai-platform)
- [Self-hosted AI agents](https://liyagent.com/docs/overview/self-hosted-ai-agents)
- [Quickstart](https://liyagent.com/docs/get-started/quickstart)
- [Command line reference](https://liyagent.com/docs/cli/reference)

<br>

## Security

Please report vulnerabilities to security@liyagent.com and not in a public issue. See [SECURITY.md](SECURITY.md) for details.

<br>

## License

Released under the [Apache License 2.0](LICENSE).

Liyagent, Liya and TicketIQ are names of Liyagent. SAP, Salesforce, Microsoft and other product names are trademarks of their respective owners. Liyagent is not affiliated with them.

<p align="center">
  <a href="https://liyagent.com"><img src="https://liyagent.com/img/liyagent-logo.png" width="88" alt="Liyagent"></a>
</p>

<h1 align="center">Liyagent</h1>

<p align="center"><strong>Self-hosted AI agents that ask before they act.</strong><br>
<sub>The <code>liya</code> command line, the audit-bundle verifier, examples and documentation.</sub></p>

<p align="center">
  <a href="https://liyagent.com">Website</a> ·
  <a href="https://liyagent.com/try">Try it live</a> ·
  <a href="https://liyagent.com/docs">Documentation</a> ·
  <a href="https://liyagent.com/docs/cli">CLI guide</a> ·
  <a href="SECURITY.md">Security</a>
</p>

---

[Liyagent](https://liyagent.com) runs AI agents inside the systems a company already uses — IT service desks, HR, SAP, Salesforce, Dynamics 365 and finance — and keeps them accountable: every agent acts as the person who asked, with that person's permissions; writes wait for a person's approval; spend is capped per agent; and every action lands in a hash-chained audit log whose signed exports anyone can verify. It runs on your own infrastructure, with the model you choose.

This repository is the **open part** of Liyagent, under the Apache License 2.0. The platform itself is commercial software that you host yourself; try it without signing up at [liyagent.com/try](https://liyagent.com/try), or write to sales@liyagent.com.

## What's in this repository

| Path | What it is |
| --- | --- |
| [`liya/`](liya) | **`liya`**, the command line for a Liyagent instance. Agents, tickets, triggers, providers and models, guardrails, secrets, Cedar policies, budgets, connectors, the knowledge base and the audit log — plus `liya apply` for agents-as-code and `liya run claude` to route a coding agent through the AI Gateway. Every command calls the same REST API as the web console. |
| [`tools/verify_audit_bundle.py`](tools/verify_audit_bundle.py) | A **standalone verifier** for Liyagent audit evidence bundles. One file, no access to the instance needed: it checks the Ed25519 signature against the instance's published keys, the hash chain, the archive segments and every file hash. |
| [`examples/liyagent_guard.py`](examples/liyagent_guard.py) | **Liyagent as the policy decision point for your own agent framework.** Your agent keeps calling its own tools; this file asks Liyagent's decision API before each call (and after, for what comes back), so the Cedar policies, guardrails and approval postures you set in Liyagent hold there too. Standard library only. |
| [`examples/ci/liyagent.yml`](examples/ci/liyagent.yml) | **Agents as code in GitHub Actions:** plan on a pull request, apply on merge, with a service-account credential rather than a person's password. |
| [`docs/`](docs) | The documentation and labs published at [liyagent.com/docs](https://liyagent.com/docs), as Markdown. |

## Install `liya`

Python 3.10 or newer.

```bash
pipx install "git+https://github.com/liyagent/liyagent.git"      # or: pip install ...
liya --version
```

Point it at an instance, sign in, and look around:

```bash
liya env add prod --url https://liyagent.example.com --use
liya auth login
liya status                      # gateway, model chain and connector health
liya agents list                 # every agent and its model binding
liya agents chat <agent-id> "What changed in the service desk this week?"
liya audit search outcome=denied --since 24h   # what was refused, and by which policy
```

Output is a table by default; `-o json` or `-o yaml` for scripts, and `liya completion` prints a shell completion script. The full command reference is at [liyagent.com/docs/cli/reference](https://liyagent.com/docs/cli/reference).

### Agents as code

Export what an instance has, keep it in git, and apply it like infrastructure:

```bash
liya export -o ./liyagent              # agents, providers, guardrails, policies, triggers — never secrets
liya apply -f ./liyagent --dry-run     # prints a diff; exits 5 if changes are pending
liya apply -f ./liyagent --reason "widen the HR agent's budget for quarter-end"
```

`--reason` is recorded in the audit log for any change that weakens a control. Before a change ships, gate it on the agent's own evaluations:

```bash
liya agents eval service-desk --baseline pinned   # exit 0 on pass, 1 on a failure or regression
```

[`examples/ci/liyagent.yml`](examples/ci/liyagent.yml) wires both into GitHub Actions: plan and evaluate on a pull request, apply on merge.

## Verify an audit evidence bundle

An instance exports its audit log as a signed bundle; anyone can check one without trusting the server that produced it. Either with the CLI:

```bash
liya audit verify audit-evidence-2026-10-06.zip --audit-keys keys.json
```

or with the single-file verifier and nothing but `cryptography`:

```bash
pip install cryptography
curl -s https://liyagent.example.com/.well-known/liyagent-audit-key.json -o keys.json
python tools/verify_audit_bundle.py audit-evidence-2026-10-06.zip --keys keys.json
```

| Exit code | Meaning |
| --- | --- |
| `0` | Verified: the signature matches a published key, the hash chain is unbroken, every file hash matches |
| `2` | A finding — something in the bundle does not check out; the output says what |
| `3` | Intact, but no key was given to trust the signer by |
| `1` | The bundle could not be read |

How the log is built, and what a bundle contains, is described in [Audit log](https://liyagent.com/docs/monitor/audit-log).

## Use Liyagent's governance from your own agent

```python
from liyagent_guard import Guard, Denied, PendingApproval

guard = Guard("https://liyagent.example.com", token=os.environ["LIYAGENT_AGENT_TOKEN"])

@guard.tool(writes=True)                 # policy check before the call, screening after
def refund(order: str, amount: int) -> str:
    ...

try:
    refund("SO-1042", 120)
except PendingApproval as p:             # a person must approve; call again with approval_id=p.id
    ...
except Denied as d:                      # a Cedar policy or guardrail said no, and why
    ...
```

Fail-closed by design: if Liyagent cannot be reached, the call is not made. See [`examples/liyagent_guard.py`](examples/liyagent_guard.py).

## Documentation

Start with [What is an agentic AI platform?](https://liyagent.com/docs/overview/agentic-ai-platform) and [Self-hosted AI agents](https://liyagent.com/docs/overview/self-hosted-ai-agents), then the [Quickstart](https://liyagent.com/docs/get-started/quickstart). The same pages are in [`docs/`](docs) here as Markdown.

## Security

Report a vulnerability to **security@liyagent.com**, never in a public issue. Details in [SECURITY.md](SECURITY.md).

## Licence

Apache License 2.0 — see [LICENSE](LICENSE). Liyagent, Liya and TicketIQ are names of Liyagent. SAP, Salesforce, Microsoft and other product names are trademarks of their owners; Liyagent is independent of them.

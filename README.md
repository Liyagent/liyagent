# Liyagent

**Governed AI agents that do the work inside the systems a company already runs** — the IT
service desk, HR, SAP, Salesforce and finance — with every risky step held for a person to
approve and every step recorded in a tamper-evident audit log.

- Website: <https://liyagent.com>
- Try Liya on a sample CRM, no sign-up: <https://liyagent.com/try>
- Documentation: <https://liyagent.com/docs>

This repository holds the **open parts** of Liyagent. The Liyagent server itself is
commercial software, self-hosted in your own cloud or data centre; talk to us at
sales@liyagent.com.

## What is here

| Path | What it is |
| --- | --- |
| [`liya/`](liya) | `liya`, the command line for a Liyagent instance: agents, evaluations, budgets, guardrails, triggers, audit, tickets, GitOps (`liya plan` / `liya apply`) |
| [`tools/verify_audit_bundle.py`](tools/verify_audit_bundle.py) | A standalone verifier for Liyagent audit evidence bundles: checks the Ed25519 signature against the instance's published keys, the hash chain, archive segments and file hashes — no access to the instance needed |
| [`examples/`](examples) | `liyagent_guard.py` (use Liyagent's policies, guardrails and approvals from your own agent framework) and a CI example that gates an agent's release on its evaluations |
| [`docs/`](docs) | The documentation and labs published at liyagent.com/docs, as Markdown |

## Install the command line

```bash
pipx install "git+https://github.com/liyagent/liyagent.git"
liya env add mine --url https://liyagent.example.com --use
liya login
liya agents list
```

## Verify an audit evidence bundle

```bash
pip install cryptography
curl -s https://<your instance>/.well-known/liyagent-audit-key.json -o keys.json
python tools/verify_audit_bundle.py audit-evidence-2026-10-06.zip --keys keys.json
```

Exit codes: `0` verified, `2` a finding, `3` intact but no key given to trust the signer
by, `1` the bundle could not be read.

## Security

See [SECURITY.md](SECURITY.md) to report a vulnerability.

## Licence

Apache License 2.0 — see [LICENSE](LICENSE). Liyagent, Liya and TicketIQ are names of
Liyagent. SAP, Salesforce and other product names are trademarks of their owners;
Liyagent is not affiliated with them.

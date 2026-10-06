---
title: GitOps with liya
order: 4
summary: Export agents, providers, guardrails, policies and triggers as YAML, review changes as a diff, and apply them from CI.
---

`liya export` writes an instance's configuration as YAML files you can commit. `liya apply` makes an instance match those files, and `--dry-run` shows you the diff first.

## Export

```bash
liya export -o infra/
```

This writes one file per resource:

```text
infra/agents/<name>.yaml       kind: AgentBundle   the server's own agent bundle
infra/providers/<name>.yaml    kind: Provider      never an API key or other secret value
infra/guardrails/<name>.yaml   kind: Guardrail
infra/policies/<name>.yaml     kind: Policy        Cedar
infra/triggers/<name>.yaml     kind: Trigger
```

Every document has the same shape:

```yaml
apiVersion: ticketiq.io/v1
kind: Trigger
metadata:
  name: nightly-digest
spec:
  agent: copilot
  kind: cron
  schedule: "0 2 * * *"
  timezone: Europe/London
  input: Summarise yesterday's tickets
```

Each `spec` holds exactly the fields that the server's own request schema accepts for that resource, which `liya` reads from the server's `/openapi.json`. Timestamps, etags and other server-managed fields are left out, so two exports diff cleanly. Fields that hold secret values (`api_key`, `…secret`, `…password`, `…token`, `credentials_json`) are never exported. A trigger's `kind` is the server's name for it: `cron`, `ticket`, `webhook`, `email`, `teams`, `slack` or `google_chat`. Fields that point to a stored secret (`…_ref`) are kept.

To export only some kinds, pass `--kind Agent --kind Policy`.

## Plan, then apply

```bash
liya apply -f infra/ --dry-run      # a unified diff per resource; exit 5 if anything would change
liya apply -f infra/                # make it so
liya apply -f infra/triggers/nightly-digest.yaml
```

`-f` takes a single file or a directory. A directory is read recursively for `*.yaml`, `*.yml` and `*.json`, and multi-document YAML files work. Resources are applied in dependency order: providers, guardrails, policies, agents, then triggers.

- **Agents** go through `POST /api/agents/apply`, in one transaction with every gate the console applies. A dry run shows the server's own plan: which sections would change, or why it would be refused.
- **Other kinds** are compared with what is on the server over every field the `PUT` writes, and then written. A `PUT` replaces the whole record, so a field you leave out of the file is reset to its default: the diff shows it as a change rather than calling the resource unchanged. Fields the server manages (timestamps, etags) and secret values are never compared. A resource that already matches is reported as `unchanged` and not written.
- If a change weakens a control, the server asks for a reason. Pass it with `--reason "…"`.

A file that contains a secret value is refused before anything is sent. Store the secret with `liya secrets set` and refer to it with a `…_ref` field.

If the connected server has no endpoint for a kind, that kind is reported as **not supported by this server version** and skipped. The rest of the run continues.

## In CI

```yaml
- name: Plan
  run: liya apply -f infra/ --dry-run      # exit 5 = changes pending, 2 = invalid, 3 = auth, 1 = other
  env:
    LIYA_URL: https://ticketiq.example.com
    LIYA_TOKEN: ${{ secrets.LIYA_SERVICE_ACCOUNT }}   # svc/<name>:<secret>
- name: Apply
  if: github.ref == 'refs/heads/main'
  run: liya apply -f infra/ --reason "merged ${{ github.sha }}"
```

The `tiq` bundle commands (`plan`, `apply`, `delete -f`) still work through `liya` for pipelines that already use them. See `examples/ci/ticketiq.yml`.

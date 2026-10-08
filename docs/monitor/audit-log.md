---
title: Audit log
order: 3
preview: true
summary: Search every action and gateway decision, group rows by request, verify the hash chain and export evidence.
outcomes: Filter the audit log by actor, action, outcome and time; Export rows and download an evidence bundle; Verify the log has not been altered; Let an auditor verify a bundle with the published key alone
---

> [!PREVIEW]
> The audit explorer is being redesigned around facets and request grouping. The query API below is current.

## Search

1. Open **Governance** › **Audit log**. Pick a time range: Last 15 min, Last 1 hour, Last 6 hours, Last 24 hours, Last 3 days, Last 7 days (the default), Last 14 days, Last 30 days, Last 90 days, All time or Custom range.
2. Narrow with facets.

   | Facet | Example |
   | --- | --- |
   | Actor, Actor type | `alice`, `human`, `agent`, `client` |
   | Action | `guardrail.save`, `budget.fallback` |
   | Resource type, Resource name | `Agent`, `hr-helper` |
   | Outcome, Response code | `denied`, `403` |
   | Subsystem, Service | The part of the product that wrote the row, or a connector |
   | Finding action, category, engine, family, policy | Guardrail findings |

3. Type free text, or `field=value` / `field!=value`, in the search box. **Search all fields** (the default) matches the action, the actor and every detail value. **Search messages** matches only each row's one-line message.
4. Turn on **Group by request** to see every row one request produced together.

The same search as an API call:

```bash
curl -G https://<host>/api/audit/query -H "Authorization: Bearer $TOKEN" \
  --data-urlencode 'q=actor=alice outcome=denied' --data-urlencode 'window=24h' \
  --data-urlencode 'page_size=50'
```

`GET /api/audit/query` accepts `q`, `window`, `since`, `until`, `page_size`, `page_token`, `order_by`, `fields`, `facet`, `match=all|message` and `group`. `window` defaults to `7d`. One event: `GET /api/audit/events/{event_id}`.

## Export and evidence

- `GET /api/audit/export?fmt=csv` (or `fmt=jsonl`) exports the filtered rows: 10,000 by default, `limit` up to 50,000. Requires `audit.read`.
- **Retention & evidence** → **Download evidence bundle** (or `GET /api/audit/export?fmt=bundle`) produces a zip of the whole hash-chained log and a manifest naming every file's SHA-256, the row count, the chain head and the checkpoints. The manifest carries two signatures:
  - an **Ed25519 attestation** with the instance's audit signing key, whose public key anyone can have, so a third party can check the bundle with no access to the instance.
  - an **HMAC** with the instance's audit key, kept for existing verifiers. Only the host can check it.

### Verify a bundle without instance access

1. Get the instance's public audit signing keys once, and keep them: `GET /api/audit/signing-key` (requires `audit.read`), or the public `GET /.well-known/liyagent-audit-key.json`. Each key lists its `fingerprint` (SHA-256 of the raw public key), its `status` and its validity window (`valid_from`, `valid_until`).
2. Run the standalone verifier. It needs Python 3.9+ and the `cryptography` package, and nothing from the instance:

   ```bash
   curl -s https://<host>/.well-known/liyagent-audit-key.json > audit-keys.json
   python scripts/verify_audit_bundle.py bundle.zip --keys audit-keys.json
   # or pin one key: --fingerprint <sha256 hex>
   ```

   It checks the Ed25519 signature on the manifest against the published keys, the bundle's date against the key's validity window, every row's hash and link, the archive segments, the anchored checkpoint, and the rows file and evidence files against the manifest. Exit codes: `0` intact and signed by a published key, `2` a finding, `3` intact but no published key or fingerprint was given to trust the signer by, `1` unreadable.

The verifier cannot check the HMAC signatures on checkpoints and on rows redacted by an erasure. Those need the instance's key. `tiq audit verify bundle.zip` (also `liya audit verify`) checks everything on the host with `--local-key`, and the attestation with `--audit-keys audit-keys.json`.

### Rotate the audit signing key

`POST /api/audit/signing-key/rotate` (requires `governance.write`, audited as `audit.signing_key.rotate`) makes a new active key. The old key stops signing at once, its private half is deleted and its validity window ends. Its public key stays listed, so the bundles it signed still verify. If the key leaked, send `{"compromised": true, "reason": "…"}`: the old key is listed as `revoked`, and verifiers refuse what it signed.

## Integrity and retention

- Rows are hash-chained. **Verify chain now**, or `GET /api/audit/verify` (requires `audit.read`, rate-limited), walks the live chain with the instance's key and names each edited, deleted or reordered row and any forged checkpoint.
- **Keep rows for (days)** and **Legal hold** are set under **Retention & evidence** (`GET` / `PUT /api/audit/retention`, where `PUT` requires `admin.write`).

> [!NOTE]
> Request bodies are never captured on sign-in, token, OAuth or secret endpoints, whatever the capture settings.

## Next steps

- [Lab: Query the audit log](/docs/labs/query-audit-log)
- [Access](/docs/govern/access)

---
title: Query the audit log
summary: Answer real questions from the audit log (who changed a guardrail, what an agent was refused), export the rows and verify an evidence bundle offline.
category: Governance
stack: [Docker]
level: Beginner
time: 20 min
order: 10
outcomes: Write audit queries with facets and free text; Group rows by request; Export and verify evidence
---

## Prerequisites

- A running Liyagent instance with some activity (any earlier lab will do).
- A user with `audit.read`.

## Steps

1. **Who changed guardrails this week?** Open **Audit log**, choose **Last 7 days**, type `subsystem=guardrail` in the search and set **Actor type** to `human`.
2. **What was refused in the last day?** Set **Last 24 hours** and **Outcome** = `denied`. Turn on **Group by request** to see each refused request with everything it touched.
3. Run the same query from the terminal:

   ```bash
   curl -b cookies.txt -G http://127.0.0.1:8787/api/audit/query \
     --data-urlencode 'q=outcome=denied' --data-urlencode 'window=24h' \
     --data-urlencode 'page_size=20' | jq '.events[] | {actor, action, outcome}'
   ```

4. Export for a reviewer: `GET /api/audit/export?fmt=csv&window=7d`.
5. Verify the hash chain: `GET /api/audit/verify`.
6. Under **Retention & evidence**, choose **Download evidence bundle** (`GET /api/audit/export?fmt=bundle`), then verify it offline:

   ```bash
   tiq audit verify audit-evidence-<date>.zip
   ```

> [!TIP]
> The verifier reads only the zip, with no network or sign-in. An auditor who has nothing of yours but the bundle and your published audit key (`/.well-known/liyagent-audit-key.json`) runs `python scripts/verify_audit_bundle.py <bundle> --keys audit-keys.json`, which checks the manifest's Ed25519 signature as well as the hash chain.

## Next steps

- [Audit log](/docs/monitor/audit-log)

---
title: Create a PII guardrail
summary: Start from the PII protection template, add an employee-number pattern rule, test both, roll them out in monitor mode and then enforce them.
category: Governance
stack: [Docker]
level: Beginner
time: 20 min
order: 6
outcomes: Create a guardrail from a template; Preview it on sample sentences; Move from monitor to enforce with evidence from the audit log
---

## Prerequisites

- A running Liyagent instance with an agent that calls a model (Liya is fine).

## Steps

1. Open **Guardrail rules** → **Create guardrail** and pick the **PII protection** template (direction **both**, action **mask**). Name it `pii-lab`.
2. Under **Rollout**, keep **Monitor first — recommended**. Under **Scope** → **Agents**, enter the agent's id, or leave it blank for every agent. Choose **Create guardrail**.
3. Create a second rule for the employee number: **Create guardrail** → **Start blank**, name `pii-lab-emp`, policy **Custom patterns**. Choose **+ Add pattern**: name `employee-number`, pattern `EMP-[0-9]{6}`, **Mask**. Keep **Monitor first** and create it.
4. In the test panel on the **Guardrail rules** list, enter `Please reset MFA for sam@example.com, EMP-204511, phone +44 20 7946 0000` and choose **Run against enabled policies**. The email and phone number come from `pii-lab`, and the employee number from `pii-lab-emp`.
5. Send the same sentence to the agent on its **Playground** tab. The answer is unchanged (monitor mode), but the audit log has findings.
6. Open **Audit log** and filter **Finding policy** = `pii-lab` (then `pii-lab-emp`). Confirm each finding is right.
7. On the list, open each rule's menu and choose **Enforce now**. Send the sentence again: the model now sees masked values.

## Check your work

```bash
curl -b cookies.txt -X POST http://127.0.0.1:8787/api/guardrails/preview \
  -H "Content-Type: application/json" -d '{"text":"EMP-204511 cannot log in"}'
```

The response names `pii-lab-emp` and its `employee-number` match: under `monitored` while the rule is in monitor mode, and under `applied` once it is enforced.

## Next steps

- [Create a guardrail](/docs/ai-gateway/create-guardrail)
- [Query the audit log](/docs/labs/query-audit-log)

---
title: Create a guardrail
order: 5
preview: true
summary: Create a guardrail from a template or from blank, set its checks and actions, test it and bind it to an agent.
outcomes: Create a guardrail from the PII protection template; Test it against sample sentences; Bind it to an agent in monitor mode and then enforce it
---

> [!PREVIEW]
> This page uses **Guardrail rules**, the per-rule console (`PUT /api/guardrails/{name}`). The newer **Guardrails** page has its own create flow for guardrails attached to LLM providers and agents.

## Prerequisites

- The **admin** or **owner** role.
- An agent to protect. The built-in Liya agent works.

## Steps

1. Open **Guardrail rules** and choose **+ Create guardrail**.
2. Pick a template ("Start from a working policy, or begin blank."). For this guide choose **PII protection**.
3. Name it, for example `pii-standard`, and set how and where it runs.

   | Field | Value for this guide |
   | --- | --- |
   | Rollout | **Monitor first — recommended** |
   | Direction | Both |
   | Agents | Blank for all agents, or name one |

4. Review the policy the template set: **Redact PII** with **Mask**, in both directions, for the default identifier types (email, phone, card numbers, IBANs, national IDs and tokens). Under **Entities** you can narrow the types, and choose an action per type if you need to:

   | Type | Suggested action |
   | --- | --- |
   | Email | Mask, or **Tokenise** to keep replies personal |
   | Phone | Mask |
   | Card number | Block |
   | National ID | Block |

5. Choose **Create guardrail**.
6. For an identifier of your own, for example an employee number `EMP-\d{6}`, create a second guardrail of kind **Custom patterns** with action **Mask**.
7. Test it: in the **Dry run** panel on **Guardrail rules**, enter `Reset the laptop for jane.doe@example.com, badge EMP-104233` and choose **Run against enabled policies**. The result shows what each policy, including those in monitor mode, would do and the text after it. See [Test a guardrail](/docs/ai-gateway/test-guardrail).
8. To hold one agent to it, choose **+ Bind an agent** under **Per-agent bindings**, tick the guardrail and choose **Create binding**. Left with no agents named, it already covers every agent.
9. Send a few real messages. In monitor mode its matches are listed for review; mark each **False positive** or **Correct**.
10. When the matches look right, choose **Enforce now** on its row.

> [!WARNING]
> Output-side masking changes what users see. Check that answers still read well, especially for templates that mask names.

## With the API

```bash
curl -X PUT https://<host>/api/guardrails/pii-standard \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d @pii-standard.json
```

## Next steps

- [Guardrail templates](/docs/ai-gateway/guardrail-templates)
- [Redaction](/docs/govern/redaction)
- [Lab: Create a PII guardrail](/docs/labs/pii-guardrail)

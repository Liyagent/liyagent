---
title: Guardrail templates
order: 6
preview: true
summary: The starting points offered when you create a guardrail, and what each one turns on.
outcomes: Pick the right template for a risk; Know what to adjust after starting from a template
---

> [!PREVIEW]
> These are the templates offered by **+ Create guardrail** on **Guardrail rules**. The newer **Guardrails** page offers its own set: Blank, Content safety, PII protection, Prompt attack defense and ITSM safe-reply.

| Template | Turns on | Typical adjustments |
| --- | --- | --- |
| Start blank | Nothing | Build your own |
| PII protection | Redact PII in both directions, masking emails, phone numbers, cards, IBANs, national IDs and tokens | Choose Mask, Tokenise or Block per type |
| Prompt attack defense | Block prompt injection on input | Monitor first, then tune for your tools |
| Secrets and credentials | Custom patterns in both directions for cloud keys, private keys and platform tokens: masked, with private keys blocked | Block more of them |
| Profanity | Word filter with the managed profanity list, masking replies | Add your own words |
| Content safety | Harm categories scored in both directions, starting in monitor mode. Self-harm and harassment escalate to a person, and the rest block | Tune each category's threshold on live scores |
| Confidential HR topics | Deny topics: Salary and pay, Redundancy and job cuts, HR case (an HR case is flagged for a person on the way in) | Escalate to HR instead of blocking |

> [!TIP]
> Templates are only a starting point. Everything they set can be changed before and after you save.

## Next steps

- [Create a guardrail](/docs/ai-gateway/create-guardrail)

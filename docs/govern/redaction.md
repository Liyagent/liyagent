---
title: Redaction
order: 5
summary: Keep personal data away from models with reversible tokens, and keep sensitive knowledge away from channels with sensitivity labels.
outcomes: Tokenize PII so models never see it; Label knowledge by sensitivity and set channel ceilings
---

## Tokenize PII

A guardrail rule of type **Redact PII** with the action **Tokenise** replaces identifiers with placeholders such as `[EMAIL_1]` before the text reaches a model.

- A placeholder stays the same for the whole conversation, so the model can still reason about "the same person".
- Real values are restored only inside the trust boundary: in the final answer shown to the user and in tool arguments.
- A placeholder the model invents is flagged in the audit log as `pii.token.unknown`.
- A conversation's token map is sealed with the vault and kept for 24 hours after its last write (`TICKETIQ_PII_TOKEN_TTL_S`).

Other actions for PII are **Mask** (replace with a typed placeholder such as `[EMAIL]`, not reversible) and **Block** (refuse the whole call). To see what a rule would catch without acting, run its policy in monitor mode. See [Create a guardrail](/docs/ai-gateway/create-guardrail).

## Sensitivity labels

Each ticket and knowledge item has a label, lowest to highest: public, internal, confidential, restricted (change the set with `TICKETIQ_SENSITIVITY_LABELS`).

- Each surface knowledge is answered through (self-service, Microsoft Teams, A2A, the case co-pilot, Liya Scribe input, MCP tools) has a ceiling, applied as a filter on the vector search, so items above it are never retrieved there. When several ceilings apply to one call, the lowest wins.
- Unlabelled items get `TICKETIQ_SENSITIVITY_DEFAULT` (internal). A source value with no mapping gets the highest label.
- PII or secrets found at ingest raise an item's label to at least `TICKETIQ_SENSITIVITY_RAISE_TO` (confidential).
- Change a label by hand with `PUT /api/tickets/{ticket_id}/sensitivity` or `PUT /api/kb/{ref_id}/sensitivity`. Lowering a label needs `governance.write` and a reason, and is audited. Loosening a surface's ceiling needs `governance.weaken` and a reason.

> [!TIP]
> Set the Microsoft Teams ceiling to internal, so a confidential HR document can't be quoted in a chat.

## Next steps

- [Lab: Create a PII guardrail](/docs/labs/pii-guardrail)

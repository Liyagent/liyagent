---
title: Semantic answer cache
order: 5
summary: Answer a question that means the same as an earlier one with the earlier verified answer, without a model call, and without crossing access boundaries.
outcomes: Turn the cache on and tune its threshold and lifetime; Explain which answers are eligible to be cached; Approve, inspect and purge cached answers
---

## What it does

When someone asks a question that means the same thing as one already answered, TicketIQ can serve the earlier answer instead of calling a model again. Only **verified** answers are reused:

- an answer someone gave a thumbs-up to,
- an answer an operator approved, or
- when `verify_kb_grounded` is on, an answer grounded only in approved, human-written KB articles.

A thumbs-down removes the entry immediately.

## Safety fences

- Lookups never cross a tenant or an agent.
- An entry is served only when the asker's own retrieval, under their access rules and sensitivity ceiling, returns every source the answer was grounded in, with the same content. If a source changed or the asker can't see it, the question goes to the model.
- Answer text is sealed with the tenant's vault key, and expired entries are pruned.

## Turn it on

1. On **AI Gateway › Cost and usage**, find **Answer caches** and set the similarity and expiry there, or call `PUT /api/semantic-cache`.

   | Setting | Default | Meaning |
   | --- | --- | --- |
   | `enabled` | false | Master switch for this scope |
   | `threshold` | 0.95 | Similarity needed to reuse an answer |
   | `ttl_s` | 604800 | Lifetime of an entry (7 days) |
   | `verify_kb_grounded` | false | Treat KB-grounded answers as verified |

2. Ask a question through Liya and give the answer a thumbs-up.
3. Ask it again in different words. The reply is served from the cache.

Tenants can override the instance settings. `TICKETIQ_SEMANTIC_CACHE=off` switches the cache off for the whole instance, whatever is stored.

## Manage entries

| Task | Endpoint |
| --- | --- |
| List entries | `GET /api/semantic-cache/entries` |
| Approve an entry | `POST /api/semantic-cache/entries/{id}/approve` |
| Drop one entry | `DELETE /api/semantic-cache/entries/{id}` |
| Drop all, or one tenant's | `POST /api/semantic-cache/purge` |

> [!WARNING]
> Purge after a knowledge-base clean-up. Entries are re-checked against their sources, but a purge removes any doubt.

## Next steps

- [Knowledge](/docs/service-desk/knowledge)
- [Lab: Use the semantic cache for repeat questions](/docs/labs/semantic-cache)

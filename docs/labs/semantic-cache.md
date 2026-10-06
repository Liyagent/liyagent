---
title: Use the semantic cache for repeat questions
summary: Turn on the semantic answer cache, verify an answer with a thumbs-up, and watch a reworded question get answered without a model call.
category: Service desk
stack: [Docker, Teams]
level: Beginner
time: 15 min
order: 11
outcomes: Enable the cache for a tenant; Create a verified entry; Confirm a cache hit and purge it
---

## Prerequisites

- A running Liyagent instance where Liya answers questions (a model is configured).

## Steps

1. Turn the cache on.

   ```bash
   curl -b cookies.txt -X PUT http://127.0.0.1:8787/api/semantic-cache \
     -H "Content-Type: application/json" -d '{"enabled": true, "threshold": 0.95, "ttl_s": 604800}'
   ```

2. Ask Liya (web chat or Teams): `How do I reset my VPN token?`
3. Give the answer a thumbs-up. It is now a verified entry: `GET /api/semantic-cache/entries`.
4. Ask it differently: `What's the way to reset the token for VPN?` The answer arrives immediately. The usage row shows no model tokens.
5. Give that answer a thumbs-down. The entry is dropped at once, and the next ask goes to the model.
6. Purge everything when done: `POST /api/semantic-cache/purge` with the body `{}`.

> [!NOTE]
> An entry is only served if your own retrieval returns every source the answer used, with the same content. Change a source article and the cache steps aside.

## Next steps

- [Semantic answer cache](/docs/service-desk/semantic-cache)

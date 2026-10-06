---
title: API overview
order: 50
summary: How to authenticate to the Liyagent HTTP API, the conventions it follows and where to find every endpoint.
outcomes: Get a session or token to call the API; Use idempotency keys, ETags and field masks
---

## Base URL

All endpoints are under `https://<host>/api/`. The OpenAPI schema is served at `/openapi.json`; the [API endpoints](/docs/reference/api-endpoints) page lists every operation from it.

## Authentication

| Caller | How |
| --- | --- |
| A person | `POST /api/login` returns a session cookie (`tiq_session`) and the same token in the body, usable as `Authorization: Bearer`; SSO starts at `/api/auth/sso/{name}/start` |
| A service account (CI, the `liya` CLI) | Client credentials at `POST /api/service-accounts/token` return a one-hour bearer with the account's permissions. Service accounts are created on **Access** → **Service accounts** or with `POST /api/service-accounts` |
| A self-managed agent | An access token from its credential's client-credentials grant at `POST /api/gateway/oauth/token` (or a static agent token) as `Authorization: Bearer`, for `/api/gateway/v1/*` |
| An integration | The instance API key as `X-API-Key`, for `/api/intake` and the agent surface |
| An OAuth client | Client credentials at the OAuth token endpoint |

```bash
curl -c cookies.txt -X POST https://<host>/api/login \
  -H "Content-Type: application/json" -d '{"username":"admin","password":"..."}'
curl -b cookies.txt https://<host>/api/me
```

## Conventions

- **Idempotency:** send `Idempotency-Key` on creates; a retry returns the first result.
- **ETags:** many resources return an `ETag`. Send `If-Match` on updates to avoid overwriting someone else's change.
- **Field masks:** some list and get routes accept `read_mask` (or `fields`) to trim responses; the endpoint's schema says which.
- **Rate limits:** a 429 carries `Retry-After` and `x-ratelimit-*` headers.
- **Errors:** a JSON body with `detail`; 422 names the invalid field.

> [!NOTE]
> Everything the console does is one of these calls, so the browser's network tab is a good way to find the endpoint for a task.

## Next steps

- [API endpoints](/docs/reference/api-endpoints)

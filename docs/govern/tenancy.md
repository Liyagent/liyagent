---
title: Tenancy
order: 6
summary: Run several customers or business units on one instance with server-enforced separation, per-tenant settings and optional per-tenant keys.
outcomes: Create a tenant and bind sources to it; Grant users access to tenants; Retire a tenant
---

## How separation works

- A tenant owns **sources**. A ticket belongs to the tenant of the source it arrived through. A ticket filed in the console belongs to the caller's selected tenant.
- Users are granted specific tenants, or `*`. Owners see every tenant.
- Reads and writes are scoped by tenant on the server, over one shared database. Cedar policies can also test the tenant.
- Budgets, the semantic cache, the learned taxonomy, retention windows and data residency can differ per tenant.
- On a multi-tenant instance, channels with no signed-in person (Teams, the answer API) must be bound to one tenant, and refuse to answer until they are.

## Create a tenant

1. Open **Tenants** and add one (`PUT /api/tenants/{tenant_id}`).

   | Field | Notes |
   | --- | --- |
   | name | Display name |
   | about | Description |
   | region | A free-text note of where its data lives. It is not enforced |
   | residency_region | Enforced: an ISO code such as `DE`, or `EU`. Model calls and embeddings for the tenant stay in that geography or are refused |
   | no_cross_geo | Also refuse cross-region routing inside the geography |
   | environment | For example `production` (the default) or `test` |
   | retention | Per-store retention windows for this tenant |
   | sources | Source ids this tenant owns |
   | owns_unsourced | Whether tickets with no source land here |

2. Bind other resources, such as agents or triggers, with `PUT /api/tenants/bindings/{kind}/{name}`.
3. Grant users with `PUT /api/tenants/grants/{username}`.
4. Users switch tenant from the console header (`POST /api/tenants/select/{id}`).

## Retire a tenant

`POST /api/tenants/{tenant_id}/retire` retires a tenant by crypto-shredding: it writes an erasure receipt, deletes the tenant, destroys its data keys (making everything sealed under them unreadable, in backups too) and removes its blobs. It needs `access.write` and `admin.write`, access to every tenant (`*`), a reason and the tenant id repeated as confirmation. It is refused unless per-tenant keys (`TICKETIQ_TENANT_KEYS`) and content sealing (`TICKETIQ_SEAL_CONTENT`) are both on and nothing the tenant owns is left outside its key, and while a legal hold covers the tenant. Each retirement's receipt is listed at `GET /api/tenants/retirements`.

> [!WARNING]
> Retirement can't be undone. Export what you need first.

## Next steps

- [Identity and roles](/docs/govern/identity-roles)

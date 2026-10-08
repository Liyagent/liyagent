---
title: Deploy on a VM
order: 3
summary: Run the production stack on one virtual machine with Docker Compose, Postgres, Qdrant and Caddy for TLS.
outcomes: Prepare deploy/.env with the required secrets; Start the stack with Docker Compose; Put Caddy in front for TLS and edge rate limits
---

## Prerequisites

- A Linux VM with Docker Engine and the Compose plugin. 4 vCPU and 16 GB RAM is a comfortable start.
- A DNS name pointing at the VM if you want a real certificate. Without one, `deploy/vm/push.sh` uses `<ip-with-dashes>.sslip.io` (for example `203-0-113-7.sslip.io`).
- Ports 80 and 443 open to the internet. Nothing else needs to be.

## What runs

| Service | Image | Exposed | Purpose |
| --- | --- | --- | --- |
| `postgres` | `postgres:16-alpine` | Not on the host | System of record (`TICKETIQ_DB_URL`) |
| `qdrant` | `qdrant/qdrant:v1.15.5` | `127.0.0.1:6341` only | Vector store for tickets and knowledge |
| `ticketiq` | Built from `deploy/Dockerfile` | `127.0.0.1:8787` | The API and console, with health check `/api/health` |
| `caddy` | Built from `deploy/caddy/Dockerfile` | 80 and 443 | TLS, edge rate limits (VM stack) |
| `mcp` | Same build | `127.0.0.1:8000` | Optional MCP server, only with `--profile mcp`. Needs `TICKETIQ_MCP_TOKEN` and `TICKETIQ_API_KEY` |

## Steps

1. Copy the example environment file and fill it in.

   ```bash
   cp deploy/.env.example deploy/.env
   ```

   | Variable | What to set |
   | --- | --- |
   | `PG_PASSWORD` | A long random string. It is fixed at first start, so don't change it afterwards. |
   | `QDRANT_API_KEY` | A long random string. |
   | `TICKETIQ_ADMIN_PASSWORD` | The first admin's password. Required on a non-loopback address. |
   | `TICKETIQ_PUBLIC_BASE_URL` | Not in the example file: add it. The external `https://` address. SSO and per-user account connections refuse to start without it, and the Teams package uses it. |
   | `TICKETIQ_BRAND_NAME` | Optional: the name shown in the console. |

2. Build and start the stack.

   ```bash
   docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build
   ```

3. Check health: `curl -s http://127.0.0.1:8787/api/health`.
4. For the VM layout with Caddy and a local model server, use `deploy/vm/docker-compose.vm.yml` and the Caddyfile beside it. `deploy/vm/push.sh <vm-ip> [domain]` ships the image and config to a VM over SSH, and `deploy/vm/update-app.sh` rolls a new build.

> [!NOTE]
> The Caddy image includes the pinned `caddy-ratelimit` module. A stock Caddy image refuses to start on the `rate_limit` directive in the Caddyfile. Caddy enforces TLS 1.2 or later, per-address request windows and tighter limits on sign-in endpoints.

## Use an external Postgres

Add the overlay and point `TICKETIQ_DB_URL` at your database, with `?sslmode=verify-full`:

```bash
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.external-db.yml up -d
```

> [!WARNING]
> Back up `pgdata` before upgrades. `deploy/backup.sh` runs `pg_dump` through `docker compose exec`, so the database never needs a host port.

## Next steps

- [Data handling](/docs/govern/data-handling)
- [Identity and roles](/docs/govern/identity-roles)
- [Microsoft Teams app](/docs/connect/teams)

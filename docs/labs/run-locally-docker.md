---
title: Run Liyagent locally with Docker
summary: Bring up Liyagent, Postgres and Qdrant with Docker Compose on your laptop, sign in and file a first ticket end to end.
category: Deployment
stack: [Docker]
level: Beginner
time: 15 min
order: 1
outcomes: Start the full stack with one compose command; Sign in and file a ticket; Tear it down cleanly
---

## What you'll build

The same stack production uses, on your laptop: `postgres`, `qdrant` and `ticketiq` from `deploy/docker-compose.yml`.

## Prerequisites

- Docker Desktop or Docker Engine with the Compose plugin.
- 4 GB of free memory for Docker.

## Steps

1. Unpack the Liyagent release. Liyagent is licensed software: request access to the release from [sales@liyagent.com](mailto:sales@liyagent.com), or [try Liya live](/try) with no install.

   ```bash
   cd liyagent        # the unpacked release
   ```

2. Create the environment file and set three secrets.

   ```bash
   cp deploy/.env.example deploy/.env
   sed -i.bak "s/CHANGE_ME_pg_password/$(openssl rand -hex 24)/; s/CHANGE_ME_qdrant_key/$(openssl rand -hex 24)/; s/CHANGE_ME_admin_password/labs-admin-pass/" deploy/.env
   ```

3. Build and start.

   ```bash
   docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build
   ```

4. Wait for health.

   ```bash
   until curl -sf http://127.0.0.1:8787/api/health; do sleep 3; done; echo " up"
   ```

5. Open `http://127.0.0.1:8787/login` and sign in as `admin` with `labs-admin-pass`.
6. Open **Tickets** and create a ticket titled `Outlook keeps asking for my password`. It is classified as **Email & Collaboration** and routed to the **Messaging Team**.
7. Check the logs if anything looks wrong: `docker compose -f deploy/docker-compose.yml logs -f ticketiq`.

> [!TIP]
> Add `--profile mcp` to the `up` command to also run Liyagent's MCP server on port 8000.

## Clean up

```bash
docker compose -f deploy/docker-compose.yml down        # keep data
docker compose -f deploy/docker-compose.yml down -v     # also delete the volumes
```

> [!WARNING]
> `down -v` deletes the Postgres volume. `PG_PASSWORD` is fixed at first start, so if you change it, delete the volume too.

## Next steps

- [Connect a Jira project and triage issues](/docs/labs/jira-triage)
- [Deploy on a VM](/docs/get-started/deploy-vm)

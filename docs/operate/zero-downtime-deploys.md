---
title: Zero-downtime deploys
order: 2
summary: Ship a new build to the VM with no 502 window - blue/green app containers, a held-not-failed edge, a durable Teams inbox, and the expand/contract rule for schema changes.
outcomes: Run the one-time cutover to blue/green; Deploy and roll back a build with no downtime; Inspect and requeue the Teams inbox; Write schema changes two builds can share
---

A deploy used to recreate the single app container, which left 30-60 seconds of 502s at the edge. Teams messages that arrived then were lost, and replies in flight were cut off. Now the new build starts beside the old one, the edge moves over once the new build is healthy, and only then is the old one stopped. The old build gets time to finish its open requests and its Teams turns before it exits.

## How a deploy runs

`deploy/vm/update-app-ssm.sh` uploads the committed source to S3 and runs the remote half on the VM through Systems Manager. The VM builds `ticketiq:<commit>` and `ticketiq-caddy:vm`, writes `Caddyfile.template`, and then runs `deploy/vm/bluegreen.py deploy --image ticketiq:<commit>`, which does the following:

1. **Takes a lock and reads the state.** It holds `/opt/ticketiq/.bluegreen.lock` so only one deploy runs at a time. It reads `bluegreen.json` and finds which colour is live: `ticketiq_blue`, `ticketiq_green`, or the old single `ticketiq` container (the one-time cutover).
2. **Checks memory.** It refuses to go on if `MemAvailable` is less than the live container's memory use plus 256 MiB. Nothing has changed at that point.
3. **Starts the idle colour on the new image** with `docker compose up -d --no-deps ticketiq_<idle>`. The new process sees the old one still holding the instance lock. It serves as the old one's successor (`TICKETIQ_INSTANCE_HANDOVER_S=600`) but does not run the schedules.
4. **Waits for health, with a timeout.** The new container must answer `/api/health` from inside itself, and Caddy must be able to reach it by name. The default timeout is 300 s (`--health-timeout`). If it crashes, restarts or times out, the deploy prints its last log lines, stops it and removes it, and exits non-zero. The live colour, the Caddyfile and the state file are exactly as they were.
5. **Switches Caddy.** It renders the Caddyfile with the new colour listed first and runs `caddy reload`. A reload is graceful: requests already in flight finish, and every new request goes to the new colour. If Caddy refuses the file, the old Caddyfile is put back and the deploy rolls back as in step 4.
6. **Records the new colour as live** in `bluegreen.json`. This is written atomically, and before anything irreversible happens.
7. **Drains the old colour** with `docker compose stop -t 150`. On SIGTERM the old process:
   - stops taking Teams inbox work at once;
   - gives open requests up to 90 s (`TICKETIQ_GRACEFUL_SHUTDOWN_S`), then Teams turns up to 45 s (`TICKETIQ_TEAMS_QUEUE_DRAIN_S`);
   - releases its advisory locks.

   Within about 10 s the new process takes the instance lock and the scheduler.
8. **Tags the image and prunes.** The new image is tagged `ticketiq:vm`, and every `ticketiq:*` image except the live and previous ones is pruned.

### The edge

Caddy lists both colours with the live one first:

```text
reverse_proxy ticketiq_blue:8787 ticketiq_green:8787 {
	lb_policy first
	lb_try_duration 30s
	lb_try_interval 250ms
	health_uri /api/livez
	...
}
```

- **`lb_policy first`** sends every request to the live colour while it is up. Login sessions are still held in each process's memory, so splitting requests between two processes would log people out at random.
- **`lb_try_duration` / `lb_try_interval`** hold a request and retry it, rather than answering 502, while no upstream is available. That covers a restart or the moment of a switch, so a Teams message arriving then is late, not lost.
- **Active health checks use `/api/livez`, not `/api/health`.** `/api/health` answers 503 when Qdrant or the disk is degraded. An edge that dropped a degraded but running app would turn a degradation into an outage of the console that reports it. The deploy itself still waits for `/api/health` before switching.

### The Teams inbox

`POST /api/teams/bots/{name}/messages` handles each activity like this:

1. It verifies the Bot Framework token as before.
2. It writes the activity to the `teams_inbox` table, sealed with the vault's data key because it is what a person typed. The row is keyed on the conversation and activity id, so a Bot Framework redelivery to either colour becomes one row.
3. Only then does it answer 200.

Every app process runs an inbox worker:

- It claims rows with `SELECT … FOR UPDATE SKIP LOCKED` under a 90 s lease, and renews the lease while the turn runs.
- A failing turn is retried with backoff (5, 10, 20, 40 s … capped at 5 min). After `TICKETIQ_TEAMS_QUEUE_MAX_ATTEMPTS` (4) it is dead-lettered with its last error.
- A process killed mid-turn leaves a row whose lease expires. The other process then claims it and runs the turn again.
- The first reply that reaches Teams marks the row `replied_at`. A row claimed again after that is finished without running the turn, so a person never gets two answers.
- Replies still go through the Bot Connector API from the worker, as before. The typing indicator and informative streaming (`start_stream`) work unchanged.

To roll back to the old in-process path, set `TICKETIQ_TEAMS_QUEUE=false` in `.env.vm` and deploy. Rows already queued are still answered, because the worker keeps running.

## One-time cutover from the single `ticketiq` container

The first run of the new `update-app-ssm.sh` on a VM that still runs the old `ticketiq` service performs the cutover. It is the same deploy, with `live = legacy`:

- `ticketiq_blue` starts beside the old container.
- Caddy is reloaded onto `ticketiq_blue`, with `ticketiq` as the fallback.
- The old container is drained for 150 s and removed.
- Caddy settles on `ticketiq_blue ticketiq_green`.
- The old container's image is kept as `ticketiq:pre-bluegreen`.

Before you run it:

1. **Check memory.** For about two minutes the old app and the new one run together. Open a Session Manager shell on the VM and run:

   ```bash
   free -m
   docker stats --no-stream
   ```

   You need free memory of at least what the `ticketiq` container uses, plus margin. If the `llm` profile runs a large model, stop it first or the deploy will refuse.
2. **Take a fresh backup** (see [Backups and restore](/docs/operate/backups)):

   ```bash
   cd /opt/ticketiq && sudo -u ubuntu bash ./backup.sh backup
   ```
3. **Make sure the Caddyfile has its site line** (an `sslip.io` address). The script builds `Caddyfile.template` from it, and stops with nothing changed if it cannot find one.

Then run, from the repo on your laptop:

```bash
git checkout main && git pull        # the commit to ship, merged
deploy/vm/update-app-ssm.sh
```

Verify:

```bash
curl -s https://liyagent.com/api/health | python3 -m json.tool | grep -A3 leader
# on the VM:
sudo python3 /opt/ticketiq/bluegreen.py status
docker ps --format '{{.Names}}\t{{.Status}}'
```

`bluegreen.py status` should show `"live": "blue"`. After the old container has stopped, the health payload's `instance_lock` should read `held`. While the old container is draining it reads `awaiting handover`. Then send the bot a message in Teams.

During the cutover only, the old container still answers Teams in-process, because it predates the inbox. A turn it has in flight when it is stopped after 150 s is lost, as before. Every deploy after this one drains through the inbox.

## Routine deploys and rollback

| Task | Command |
| --- | --- |
| Deploy the committed `HEAD` | `deploy/vm/update-app-ssm.sh` |
| See what is live | `sudo python3 /opt/ticketiq/bluegreen.py status` (on the VM) |
| Roll back to the previous build | `cd /opt/ticketiq && sudo python3 bluegreen.py rollback` |
| Deploy a specific image already on the VM | `sudo python3 /opt/ticketiq/bluegreen.py deploy --image ticketiq:<commit>` |

A rollback is an ordinary blue/green deploy of `previous_image` from `bluegreen.json`, so it has no downtime either.

> [!WARNING]
> **Rolling back past the cutover needs a short outage.** The build from before blue/green (`ticketiq:pre-bluegreen`) has no handover. Started beside a newer build, it refuses to start, and the deploy rolls itself back.

To go back to the pre-blue/green build, stop the live colour first:

```bash
cd /opt/ticketiq
DC="docker compose --env-file .env.vm -f docker-compose.vm.yml -f docker-compose.override.yml"
$DC stop -t 150 ticketiq_blue
TICKETIQ_IMAGE_GREEN=ticketiq:pre-bluegreen $DC up -d --no-deps ticketiq_green
```

Caddy falls through to green on its own. `bluegreen.py` reads the running colour as live if the state file disagrees.

## Background work during the overlap

For a minute or two, two app processes share the database and the `/data` volume. This is what keeps each kind of background work from running twice harmfully:

| Work | Where it runs | Why it cannot double-run |
| --- | --- | --- |
| The scheduler, which carries everything below | The process holding the `ticketiq:scheduler` advisory lock (`leader.py`) | The new process is not even a candidate until it holds the instance lock, which the old one holds until it exits. The schedules move over in one election round and never overlap. |
| Covered by the scheduler: source sync, mail intake, attachment extraction, cron triggers, detectors, OAuth secret rotation, audit checkpoint and prune, KB nightly and gap alerts, SLA sweep, auditor, sentinel, scribe, retention purge, `register_periodic` jobs (outbox drain, alert rules, approvals, grants, spend forecast, …) | The leader only | Same lock. Several are also safe on their own: the outbox uses `SKIP LOCKED` with leases, alert rules use per-rule advisory locks, and ticket triggers use unique claims. |
| Teams inbox | Every process | `SKIP LOCKED` claims under a lease, idempotent enqueue, and `replied_at`. A draining process stops claiming. |
| Job history recovery (marking jobs from a dead process "interrupted") | At startup, or at takeover for a successor | Deferred until the successor takes over (`JobManager.recover_once`), so the old process's running jobs are not marked interrupted while it still runs them. |
| Kill-switch and event listeners (`LISTEN`) | Every process | Per process by design: each one severs or streams for its own sessions. |
| Startup work: schema setup, vault migration, seeds, `retention.prune_runs` | The process starting up | Idempotent. Schema setup waits at most 3 s for each lock and retries (`PostgresStore._apply_schema`), so it never stalls the old build behind a queued `ALTER`. |
| Metrics OTLP push (only when `TICKETIQ_METRICS_OTLP_ENDPOINT` is set) | Every process | Each process reports its own series. A minute of two series is expected. |
| Nightly backup | Host cron, `backup.sh` | Not in the app. `backup.sh` finds the live colour itself. |

The data dir write probe is now named per process, so two containers starting together cannot fail each other's startup. `vault.key` is read-only once it exists, and the VM keeps the key in `.env.vm` anyway. Blobs are content-addressed and written atomically.

## Schema changes: expand, then contract

The new build's schema setup runs while the old build is still serving from the same database. Every schema change must therefore leave the old build working.

- **Expand (any release):**
  - Add tables.
  - Add columns that are nullable or have a constant default.
  - Add indexes, `CONCURRENTLY` for big tables (see `_ensure_indexes`).
  - Add new `kv` keys.
  - Backfill data with idempotent, batched code that tolerates rows the old build writes meanwhile.
- **Contract (a later release, once no running build reads the old shape):**
  - Drop or rename columns and tables.
  - Change a column's type.
  - Add `NOT NULL` to an existing column.
  - Remove a `kv` key or change its document shape.
- **Module DDL** created on first use takes `pg_advisory_xact_lock(hashtext('ticketiq:schema:<name>'))`, as `teamsqueue.ensure` does, so two processes do not race on `CREATE TABLE`.
- **CI guard:** `tests/unit/test_schema_additive.py` fails on new destructive DDL. Split the change, or add it to the known list with the reason it cannot break the build beside it.

## Limits

- **Everyone signs in again after a deploy.** Login sessions are still process-local (`SCALE.md`). The new process does not know the old one's, as it did not after a restart. The edge never splits requests between the two processes, so nobody flips between them mid-session.
- **Postgres has `max_connections=60`.** Two app processes each hold per-thread connections. A deploy under heavy load can briefly hit the ceiling. Raising it, together with `mem_limit`, restarts Postgres once, so do that in a maintenance window.
- **Memory.** Two app processes need room on the 4 GB VM. The deploy checks this and refuses rather than risk the OOM killer.

## Inspecting the Teams inbox

```bash
cd /opt/ticketiq
PSQL="docker compose --env-file .env.vm -f docker-compose.vm.yml exec -T postgres psql -U ticketiq -d ticketiq"
$PSQL -c "SELECT state, count(*) FROM teams_inbox GROUP BY 1"
# dead letters, newest first (no message text: done and dead rows drop it)
$PSQL -c "SELECT id, trigger, attempts, last_error, received_at FROM teams_inbox
          WHERE state='dead' ORDER BY id DESC LIMIT 20"
```

A dead row has lost its payload, so it cannot be requeued. Its `last_error` says why the turn failed. Rows in `pending` or `running` can be retried at once:

```sql
UPDATE teams_inbox SET available_at = now() WHERE state = 'pending';
```

Finished rows are deleted after 24 hours.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| Deploy stops with `not enough memory` | Too little room for two app processes | Stop the `llm` profile, or pass `--skip-memory-check` on the VM if you accept the risk |
| Deploy stops with `not healthy after 300 s` and log lines | The new build fails to start | The live colour is untouched. Fix the build, commit and deploy again |
| `/api/health` shows `instance_lock: lost` on the new colour | The old colour was still running 600 s after the new one started | Stop the old colour (`docker compose stop ticketiq_<old>`). The new one serves again once it wins the lock |
| `another deploy holds …/.bluegreen.lock` | A deploy is running, or one was killed | Wait. The lock is released when the process exits |

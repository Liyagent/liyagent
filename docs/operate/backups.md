---
title: Backups and restore
order: 3
summary: Back up the Docker stack's database, vector index and data volume, check a snapshot restores, restore one, and control how many snapshots are kept.
outcomes: Take and verify a backup; Restore a snapshot; Set how long and how many snapshots are kept
---

`deploy/backup.sh` backs up the bundled Docker stack while the app keeps serving. Each snapshot is a directory (default `backups/<utc-timestamp>`) holding:

| File | What it is |
| --- | --- |
| `ticketiq.dump` | `pg_dump -Fc` of PostgreSQL, taken inside the `postgres` container |
| `data.tar.gz` | The data volume: the token vault's sealed files, the audit checkpoint anchor and archive, blobs |
| `qdrant.tar.gz` | The Qdrant volume (the vector index) |
| `audit-anchor.json` | The audit anchor, copied before the dump so it names a checkpoint the dump holds |
| `SHA256SUMS`, `RESTORE.txt`, `.ticketiq-backup` | Checksums, manual restore steps, and the marker that identifies the directory as a snapshot |

The vault key is not in the backup when `TICKETIQ_VAULT_KEY` is set in the environment file.

> [!NOTE]
> Only the bundled `postgres` service is backed up. If `TICKETIQ_DB_URL` points at an external database (RDS, Cloud SQL), every command refuses. Use the provider's snapshots or point-in-time recovery instead.

## Commands

| Task | Command |
| --- | --- |
| Take a backup | `deploy/backup.sh backup [OUT_DIR]` |
| Check a snapshot restores (into a scratch database, dropped afterwards) | `deploy/backup.sh --verify [BACKUP_DIR]` (default: the newest under `backups/`) |
| Restore a snapshot | `deploy/backup.sh restore BACKUP_DIR` |

`--verify` and `restore` check `SHA256SUMS` before touching anything. A restore loads the dump into a new database while the app still serves, then stops the app and Qdrant, swaps the databases by rename, restores both volumes and starts the stack again. If the dump does not restore, nothing is changed. Afterwards, check **Verify chain now** on the audit log (`GET /api/audit/verify`) reports the chain intact.

On the VM, the deploy scripts copy `backup.sh` to `/opt/ticketiq` and schedule it for the `ubuntu` user at 02:30 daily (host time): a backup, then `--verify`, logged to `/opt/ticketiq/backups/backup.log`.

## Retention

Pruning runs after each successful `backup`, in the directory the snapshot was written to. It only deletes snapshot-named directories that carry the `.ticketiq-backup` marker, and never the snapshot just written.

| Variable | Default | Effect |
| --- | --- | --- |
| `BACKUP_RETENTION_DAYS` | `14` | Snapshots older than this many days are deleted. `0` turns the age limit off. |
| `BACKUP_KEEP` | `0` | Keep only this many newest snapshots. `0` sets no count limit. |

Both limits apply together. Both must be whole numbers, or the script exits before doing anything.

`BACKUP_KEEP` is read from the environment first. When it is unset, the script reads an unquoted `BACKUP_KEEP=<n>` line from `.env.vm` beside it, so the VM's nightly cron honours it. To keep the newest seven snapshots on the VM:

```bash
# /opt/ticketiq/.env.vm
BACKUP_KEEP=7
```

`BACKUP_RETENTION_DAYS` is not read from `.env.vm`. Set it in the environment of the command (or the cron line) to change it.

## Next steps

- [Zero-downtime deploys](/docs/operate/zero-downtime-deploys)
- [Audit log](/docs/monitor/audit-log)

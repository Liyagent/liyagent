---
title: Add a known-issue banner
summary: Turn an outage ticket into a known issue that absorbs repeat reports, answers each reporter on their own channel and notifies them all when it is fixed.
category: Service desk
stack: [Teams, ServiceNow]
level: Intermediate
time: 20 min
order: 12
outcomes: Open an original ticket for an outage; See repeat reports fold in as known issues; Resolve it and confirm every reporter is notified once
---

## Prerequisites

- A running Liyagent instance with the Teams bot or web chat set up, or a ServiceNow source feeding incidents.

## Steps

1. Open the outage ticket: **Tickets** → create `Email delivery delayed for all users`, priority P3.
2. From three different users, report it in different words, for example `Outlook not receiving mail` from Teams and `emails stuck in outbox` from web chat.
3. Each reporter gets a known-issue reply on their own channel (a card in Teams, a message in web chat). No new tickets appear in the queue.
4. Open the original: its reporters list (`GET /api/tickets/{id}/reporters`) shows one row per person and channel.
5. Look at the original's priority: the third report from a different person raised it one level, to P2. Keep going to six people within 24 hours and the sixth report makes it P1. Repeats from someone who already reported do not count.
6. Resolve the original. Each reporter is told once, through the outbox, so a Teams outage is retried rather than lost.
7. If one report was not really the same issue, unmerge it: `POST /api/tickets/{id}/unmerge`.

> [!TIP]
> Set `TICKETIQ_SUPERVISED_DEDUP_MERGE=true` during a major incident if you want a person to confirm each merge.

## Next steps

- [Known issues and duplicates](/docs/service-desk/known-issues)

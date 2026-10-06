---
title: Known issues and duplicates
order: 4
summary: How repeat reports are folded into one ticket, answered as a known issue on the channel they came from, and closed out for every reporter.
outcomes: Explain the duplicate thresholds and review band; Describe what a reporter sees when their report is a known issue; Undo a wrong merge
---

## How duplicates are found

Liya Correlate compares each new ticket with open tickets by vector similarity.

| Setting | Default | Meaning |
| --- | --- | --- |
| `TICKETIQ_DEDUP_THRESHOLD` | 0.72 | Similarity at or above which a ticket is a duplicate |
| `TICKETIQ_DEDUP_REVIEW_BAND` | 0.04 | Just below the threshold: flagged for a person to review |
| `TICKETIQ_DEDUP_CROSS_CATEGORY_MIN` | 0.82 | Higher bar when the two tickets are in different categories |
| `TICKETIQ_DEDUP_WINDOW_HOURS` | 336 | How far back open tickets are compared (14 days) |
| `TICKETIQ_SUPERVISED_DEDUP_MERGE` | false | Require a person to confirm every merge |

When reports keep coming from different people, the original is escalated: the third live report bumps it one priority level, and the sixth makes it P1. Repeat reports from the same person don't count, and the count resets when reports stop clustering. With `TICKETIQ_SUPERVISED_STORM_ESCALATION` on, the escalation is held in the **Inbox** under **Approvals** for a person to confirm.

## What the reporter sees

A report folded into an open original is answered as a **known issue** on the channel it came in on: a card in Teams, a message in web chat or a reply to the email. It doesn't become a new ticket in anyone's queue.

Each reporter is kept on the original, one row per person and channel (`GET /api/tickets/{id}/reporters`). When the original is resolved, every reporter is told once. Notices go through the outbox, so a Teams or SMTP outage is retried, and they are rate-limited to 5 per person per hour.

## Undo a merge

Open the duplicate on **IT service desk › Tickets** and choose **Unmerge**, or call `POST /api/tickets/{id}/unmerge`. The ticket goes back into the queue as its own case. Tick **also undo the parent's storm escalation** to put the original's priority back too.

> [!TIP]
> To announce an issue before reports arrive, see [Lab: Add a known-issue banner](/docs/labs/known-issue-banner).

## Next steps

- [Semantic answer cache](/docs/service-desk/semantic-cache)

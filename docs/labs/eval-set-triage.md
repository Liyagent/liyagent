---
title: Write an eval set for Triage
summary: Build a versioned triage dataset from real tickets, run it as a baseline, change the routing, and catch the regression.
category: Service desk
stack: [Docker]
level: Intermediate
time: 30 min
order: 8
outcomes: Create a triage dataset from tickets and JSONL; Run it and set a baseline; Use the result as a CI gate
---

## Prerequisites

- A running Liyagent instance with resolved tickets that carry triage labels: from a source that brings its own category, team and priority, or tickets where a person corrected triage. Sync a source or run the Jira lab first.

## Steps

1. Create the dataset from your labelled tickets. Every resolved ticket with triage labels in scope becomes a case:

   ```bash
   curl -b cookies.txt -X POST http://127.0.0.1:8787/api/evals/datasets/triage-core/from-tickets \
     -H "Content-Type: application/json" -d '{"limit": 500}'
   ```

2. Add edge cases as JSON Lines, one per line, with the expected category, team and priority:

   ```json
   {"id": "printer-3f", "title": "Cannot print to 3rd floor printer", "labels": {"category": "Hardware", "team": "Field Services", "priority": "P3"}}
   {"id": "ransomware", "title": "Ransomware note on finance share", "labels": {"category": "Security", "team": "Security Operations", "priority": "P1"}}
   ```

   Send them with `POST /api/evals/datasets` and `{"name": "triage-core", "kind": "triage", "append": true, "jsonl": "<the lines>"}`. Each write is a new dataset version.
3. Split it into calibrate and holdout sets: `POST /api/evals/datasets/triage-core/split` with `{"seed": 7}`.
4. Run it (`POST /api/evals/runs` with `{"dataset": "triage-core"}`) and open the run on **Evaluations**. Choose **Pin as baseline**.
5. Make a change that should hurt: route **Hardware** to **Service Desk L1** with `PUT /api/routing` and `{"table": {"Hardware": "Service Desk L1"}}`.
6. Run again. The comparison shows the Hardware cases regressing against the baseline.
7. Put the gate in CI:

   ```bash
   tiq eval run --dataset triage-core --fail-on-regression
   ```

## Clean up

`DELETE /api/routing` restores the default routing table.

## Next steps

- [Playground and evals](/docs/agents/playground-evals)

---
title: Connect a Jira project and triage issues
summary: Sync a Jira project into TicketIQ, learn categories from its history and watch new issues get classified, merged and routed.
category: Service desk
stack: [Jira, Docker]
level: Intermediate
time: 30 min
order: 2
outcomes: Add a Jira source whose API token is kept in the secrets store; Learn a taxonomy from synced issues; Verify routing on a fresh issue
---

## Prerequisites

- A running Liyagent instance ([Run Liyagent locally with Docker](/docs/labs/run-locally-docker)).
- A Jira Cloud site with a project you can read, your Atlassian email and an [API token](https://id.atlassian.com/manage-profile/security/api-tokens).

## Steps

1. Save the API token in the secrets store, so the source holds only a reference to it:

   ```bash
   curl -b cookies.txt -X POST http://127.0.0.1:8787/api/secret-store \
     -H "Content-Type: application/json" -d '{"id":"JIRA_API_TOKEN","value":"<your API token>"}'
   ```

   Or open **Secrets store** → **+ Create secret**.

2. Add a Jira source that references it:

   ```bash
   curl -b cookies.txt -X POST http://127.0.0.1:8787/api/sources \
     -H "Content-Type: application/json" -d '{"name":"Jira ITSM","type":"jira","config":{
       "base_url":"https://<site>.atlassian.net","email":"<your Atlassian email>",
       "token":"secret://JIRA_API_TOKEN","project":"ITSM"}}'
   ```

   Or in the console: **Settings** → **Data & retention**, type **Jira**, and pick `JIRA_API_TOKEN` under **API token**. Add `"jql"` for an extra filter, such as `issuetype in (Bug, Incident)`.

   > [!NOTE]
   > The token is opened from the secrets store each time the source syncs and is never stored on the source or returned by the API. A reference to a secret that doesn't exist is refused with a `422`.

3. Test the source: `POST /api/sources/{id}/test` should report a successful search.
4. Sync: `POST /api/sources/{id}/sync`. Open **Tickets**. The issues arrive already classified and routed.
5. Learn categories from the history: open **Categories** → **Learn from history** and review the proposal. Rename clusters to names your team uses and set each **Routing team**.
6. Choose **Approve taxonomy**, then **Activate**, then reclassify so the synced issues use the new categories (`POST /api/sources/{id}/reclassify`).
7. Create a new issue in Jira that repeats an existing one, sync again, and open it in TicketIQ. It is folded into the original as a known issue.

> [!NOTE]
> The connector is read-only. Nothing in this lab writes to Jira.

## Check your work

- **Categories** shows your approved taxonomy as active.
- The repeated issue is listed on the original under reporters (`GET /api/tickets/{id}/reporters`).

## Next steps

- [Triage and categories](/docs/service-desk/triage-categories)
- [Write an eval set for Triage](/docs/labs/eval-set-triage)

---
title: Connect SAP Field Service Management
nav_title: SAP Field Service Management
order: 11
summary: Connect Liya to SAP Field Service Management to read service calls and, if you switch it on, plan and release activities, with a person confirming each agent call.
outcomes: Create an FSM OAuth client that can only read one company; Add a SAP Field Service Management connection; Switch on dispatching and give the OAuth client planning rights; Explain which FSM data Liya reads and what it never asks for
---

Liyagent runs a managed **SAP Field Service Management** server. It reads service calls, activities, technicians, equipment and customers through FSM's Query API, and asks FSM's Optimization API which technicians best fit an activity.

By default the connection only reads. An administrator can switch on [dispatching](#dispatching), which lets Liya plan, release, replan, reschedule and unassign one activity at a time, or plan and release one in a single step with `assign_work`. Liya never creates, cancels, closes or completes service calls or activities.

Like the [S/4HANA and SuccessFactors connectors](/docs/connect/sap), every FSM call an agent makes waits for the person who asked to confirm it in a one-to-one chat (Teams, Google Chat or web chat) or the agent's Playground. Work with no person behind it, such as a schedule or trigger, gets no FSM call. The exception is a read routine that a person set up and confirmed in their Teams chat, such as a morning digest: the scheduler runs exactly that read, and never a write. See [Working within SAP's API Policy](/docs/connect/sap#working-within-saps-api-policy).

## Tools

| Tool | What it does |
| --- | --- |
| `list_service_calls` | Service calls, newest first: code, subject, status, priority, type, customer and equipment. Filter by status name, open ones only, priority, or one piece of equipment. |
| `get_service_call` | One service call by its code or id, with its activities. |
| `list_activities` | Activities by service call, technician, status (`DRAFT`, `OPEN`, `CLOSED`) and a start-date range. |
| `get_activity` | One activity by its code or id: status, stage, the technician it is assigned to, planned start and end, its service call and customer. |
| `find_technician` | People by first or last name: id, code, name and job title. |
| `list_equipment` | Equipment by code, serial number or name, or a customer's equipment. |
| `get_equipment` | One piece of equipment, with its ten most recent service calls. |
| `find_customer` | Customers (business partners) by code or name. |
| `list_unplanned_activities` | Activities waiting to be planned (stage `DISPATCHING`, status `DRAFT`), newest first, with their service call's code, subject and priority. |
| `get_service_call_tree` | One service call with every activity under it, including each activity's required skills, from FSM's Service Management API. |
| `technician_schedule` | One technician's day, or up to seven days: each assigned activity with its start, end, status, customer and service call, and the free time between. |
| `dispatch_digest` | The dispatcher's morning numbers: activities waiting to be planned, how many are high or urgent priority, service calls due today and activities released for today. |
| `high_priority_unplanned` | High and urgent priority activities still waiting to be planned after a number of minutes, oldest first. |
| `recommend_technicians` | FSM's own ranking of the technicians who best fit one activity: name, score, availability, travel time and distance, matching and missing skills, and a proposed start and end. It plans nothing. |
| `plan_activity` | Plans one activity: a technician, a start and a duration. [Dispatching](#dispatching) only. |
| `release_activity` | Releases one planned activity to its technician's mobile app. Dispatching only. |
| `replan_activity` | Moves one activity to another technician, with a new start and duration. Dispatching only. |
| `reschedule_activity` | Moves one activity to a new start and duration, optionally with another technician. Dispatching only. |
| `unassign_activity` | Takes one activity off its technician and returns it to planning. Dispatching only. |
| `assign_work` | Plans a service call's activity for a technician and releases it, in one confirmed step. Takes the service call (or the activity) and the technician by name or id, a start and a duration. `release: false` plans without releasing. Dispatching only. See [Assign work in one step](#assign-work-in-one-step). |
| `propose_backlog_plan` | Works out a plan for up to a set number of activities waiting to be planned, most urgent first, each with FSM's best-fitting technician and a time that overlaps nothing they already have. It plans nothing. |
| `apply_backlog_plan` | Plans, and optionally releases, the activities of a plan from `propose_backlog_plan`, in order, stopping at the first failure. The person confirms the whole plan once. Dispatching only. |

No tool takes a query. Liya builds every Query API statement itself from a fixed template, and each argument is checked and quoted before it goes in, so an agent can't compose its own request to FSM.

Every statement names the fields it reads. Liya never asks for a person's email address, phone numbers or address, a customer's contacts or credit data, or the free-text remarks on a service call or activity. `get_service_call_tree` reads an API that returns whole records, so Liya keeps only the fields it lists: an address is cut down to its city and country, and contacts and remarks are dropped.

## Create an OAuth client in FSM

Liya signs in to FSM as an OAuth 2.0 client with the client credentials grant. Give the client the least it needs:

1. In FSM, open **Account Administration** and select your account.
2. Under **Groups** (policy groups) in the company Liya reads, create a group that can only **read** service calls, activities, persons, equipment and business partners. Give it no create, update or delete permission.
3. Open **Clients**, then **Create**. Choose the **client credentials** grant and assign the client to the read-only group you created, in that one company only.
4. Copy the **Client ID** and **Client Secret**. FSM shows the secret once.
5. Note your account and company. Both are shown in Account Administration, as a name and a numeric id. Either works in Liya.

## Add the connection

1. Open **MCP servers**, choose **Add MCP server**, and pick **SAP Field Service Management** in the catalogue.
2. Fill in the settings.

   | Setting | API field | Value |
   | --- | --- | --- |
   | Cluster host | `base_url` | Your FSM cluster, such as `https://eu.fsm.cloud.sap`. Others include `us`, `au`, `de` and `cn`: use the host you sign in to FSM at, without a path. |
   | Account | `account` | The FSM account name, or its numeric id. |
   | Company | `company` | The one FSM company Liya reads, by name or numeric id. |
   | Account id | `account_id` | The account's numeric id, when **Account** is a name. Needed for `recommend_technicians`, `get_service_call_tree` and dispatching. |
   | Let Liya plan and release activities | `allow_writes` | Off by default, so the connection only reads. See [Dispatching](#dispatching). |
   | Identity | `identity` | `shared` (default) or `mapped`: whose FSM rights a call runs under. See [Act as each person in SAP Field Service Management](/docs/connect/sap-fsm-identity). |
   | Dispatch groups, Read groups | `dispatch_groups`, `read_groups` | With `mapped` only: the FSM permission groups that may dispatch, or use the connection at all. |
   | Calls a minute | `max_calls_per_minute` | Calls a minute to this account from each Liya process. Blank is 60. |

3. Under **Auth**, choose **OAuth client** and enter the client id and secret (`FSM_CLIENT_ID` and `FSM_CLIENT_SECRET` in `env`). The secret is kept in the [Secrets Store](/docs/connect/secrets).
4. Choose **Save server**, then grant the server to an agent.

Liya fetches a token at `{cluster}/api/oauth2/v2/token` and reuses it until shortly before it expires. Every request names the account and company, and says it comes from Liya (`X-Client-ID: liyagent`), so your FSM administrators can tell its traffic apart.

## Dispatching

With dispatching on, an agent can help a planner work through unplanned activities:

1. `list_unplanned_activities` finds what is waiting.
2. `recommend_technicians` asks FSM who fits best. This changes nothing in FSM.
3. `plan_activity` assigns the chosen technician, start and duration. `release_activity` then sends the activity to the technician's mobile app. `assign_work` does both, and finds the activity and technician, in one confirmed step.

`replan_activity`, `reschedule_activity` and `unassign_activity` change an activity that is already planned.

Each of these writes is a proposal. The person who asked sees the activity, its service call, the technician by name, and the start, end and duration, and the write runs only when they confirm it. To show names rather than ids, Liya looks the activity, its service call and the technician up in FSM before the proposal is shown. These lookups only read.

### Assign work in one step

A request like "assign service call 173 to Bankim tomorrow at 9 for two hours" would otherwise take four confirmations: finding the activity, finding the technician, planning, and releasing. `assign_work` does it with one.

Before anything is proposed, Liya looks up, with reads only:

- **The activity.** If the agent names an activity, that one. Otherwise the service call's one activity still waiting to be planned (stage `DISPATCHING`, status `DRAFT`). If the service call has none, or several, nothing is proposed: the agent gets the activity codes and subjects so the person can say which.
- **The technician.** By FSM id, or by name against first and last names, ignoring case. An exact full name wins, then names that start with each word given, then names that contain them. Exactly one person must match. If nobody or several people match, nothing is proposed and the agent gets the candidates' names and ids to choose from.

The person then confirms one sentence, such as *Assign service call 173 · activity 243 'Motor Heating' to Dana Reyes, 6 Oct 09:00–11:00 UTC, then release to the technician*, with the service call, activity, technician, start, end, duration and whether it is released.

Once confirmed, fixed code looks both up again by the same rules, and sends nothing if they now give a different activity or technician than the person was shown. Otherwise it plans the activity and then, unless `release` is `false`, releases it. These are the same two FSM actions that `plan_activity` and `release_activity` send. If planning succeeds but FSM refuses the release, the result says so: the activity is planned for the technician but not released, with FSM's reason. `release_activity` can then try again.

This stays within SAP's API Policy: the agent does not choose or chain FSM calls. The steps are a fixed, deterministic sequence in Liya's code, and the person confirms the whole action before any of it runs. See [Working within SAP's API Policy](/docs/connect/sap#working-within-saps-api-policy).

Release works only on an activity that is `DRAFT` or `OPEN`, in the `DISPATCHING` stage, with an assigned technician. Otherwise FSM refuses it.

### Switch on dispatching

1. In FSM's **Account Administration**, give the OAuth client's policy group planning and dispatch rights on **Activity** and **ServiceAssignment** in the company Liya uses. Keep everything else read-only.
2. Make sure the connection has the account's numeric id: either **Account** is the id, or **Account id** is set.
3. Tick **Let Liya plan and release activities** when you add the connection. The console has no **Edit** view for managed servers, so to switch it on later, send the fields with `PATCH /api/mcp/servers/{name}` and an `update_mask`:

   ```bash
   curl -X PATCH https://<host>/api/mcp/servers/fsm \
     -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d '{"update_mask": ["allow_writes", "account_id"], "server": {"allow_writes": true, "account_id": "96463"}}'
   ```

Liya checks the setting before it proposes a write, and again before it sends one. If FSM answers a write with **403 Forbidden**, Liya tells the person that the OAuth client's policy group doesn't allow planning, and nothing is changed.

For these calls Liya sends FSM both the account and company ids and their names. FSM's Optimization and Service Management APIs refuse a company given by name only. Liya looks up the company's id from your account's company list once and reuses it.

## What has been tested

The connector follows SAP's published FSM documentation: the OAuth 2 API, the request headers, the Query API, the Optimization API and the Service Management API's activity actions. On 3 October 2026 every read tool was run against a live FSM tenant, with its data object versions (such as `ServiceCall.27` and `Activity.43`) and fields. Planning and releasing one activity were also run live. `assign_work` sends those same two requests; its lookups and its sequence are covered by automated tests. Replan, reschedule and unassign follow SAP's documented requests and are covered by automated tests. If FSM rejects a data object version on your tenant, which can happen on an older release, tell us which version your tenant supports.

---
title: Act as each person in SAP Field Service Management
nav_title: SAP FSM identity
order: 11.5
summary: Choose whose FSM rights Liya's calls run under, either the connection's OAuth client or each person's own FSM user and permission group, and what your FSM administrator sets up for each.
outcomes: Choose between shared and mapped identity; Prepare FSM users and permission groups for mapped identity; Limit the OAuth client to what Liya needs; Find who did what in FSM through Liya
---

Every SAP Field Service Management call Liya makes is a proposal that the person who asked confirms in a one-to-one chat or the agent's Playground. See [Connect SAP Field Service Management](/docs/connect/sap-fsm). The connection's **identity** setting decides whose FSM rights the confirmed call runs under.

| Identity | Whose rights | Use it when |
| --- | --- | --- |
| `shared` (default) | The connection's OAuth client, the same for everyone. | Everyone who can reach Liya may see and do what the client can. |
| `mapped` | Each person's own FSM user and that user's FSM permission group. | People should see and do only what FSM already lets them. For example, technicians shouldn't be able to dispatch through Liya. |

Both modes use the same OAuth client. Neither needs a new OAuth client, a new grant type or a redirect URI, and Liya never asks anyone for their FSM password.

## Why mapped identity works this way

FSM's OAuth API issues tokens for two grants only:

- **Client credentials**: an app.
- **Password**: an account, or a company user with that user's own FSM password.

FSM has no authorization code grant for third-party apps. See SAP's *Access API (OAuth 2.0)* guide, the pages "Obtain Authorization" and "Get Access Token".

For a backend that serves many people, SAP documents a single sign-on pattern in *Extensions > Authentication > Single Sign-On*:

1. The backend keeps the FSM client credentials.
2. The backend verifies the person with your identity provider. The email address identifies the person on both sides.
3. The backend matches the person to their FSM user.
4. The backend makes requests on the person's behalf and logs every request, because FSM itself only sees the client.

Mapped identity follows this pattern.

## What mapped identity does

For every FSM call, before anything is sent:

1. **The person.** Liya takes the work email or user principal name (UPN) that Microsoft Entra ID verified for the person in Teams. A web chat person signs in to Liyagent instead. Liya never uses a display name or anything typed in the message. A shared group chat or channel is refused: the person is asked to use a one-to-one chat.
2. **Their FSM user.** Liya reads your company's FSM users and looks for exactly one user with that email that isn't deleted. The user must be active and not locked. If there is no match or more than one, Liya says why and sends nothing.
3. **Their permission group.** Liya reads the user's permission group in this company and checks the group's own FSM rights:
   - **Reads** need *read: All* on the objects the tool returns. These are Service call, Activity, Person, Equipment and Business partner. If the group can read *Own* records only, the call is refused. Liya's fixed queries can't narrow results to a person's own records, and it won't show more than FSM would.
   - **Planning and dispatching** (`plan_activity`, `release_activity`, `replan_activity`, `reschedule_activity`, `assign_work` and `apply_backlog_plan`) need *update: All* on Activity and *create* and *update: All* on Service assignment. `unassign_activity` also needs *delete: All* on Service assignment. This is what FSM's planning board needs from a planner. The connection must also have [dispatching](/docs/connect/sap-fsm#dispatching) switched on.
   - **Optional allow-lists** on the connection narrow this further:
     - `dispatch_groups`: only these permission groups may plan and dispatch.
     - `read_groups`: only these groups, or the dispatch groups, may use the connection at all.

     Name each group by its id or its name.
4. **Their FSM person.** Liya also finds the FSM Person record for the user. It's the record whose user name is the FSM user's name, or else the one active record with the same email. Liya only uses it as a label.

The confirmation card shows whom the call runs as, for example **In SAP FSM as: Ana Lopez (FSM user ana)**. If the person's FSM user changes between the proposal and the confirmation, nothing is sent and Liya asks them to ask again.

Liya keeps both listings for five minutes. A change in FSM, such as a new permission group, takes effect within that time.

## Who did what: the per-person log

FSM's own change history names the OAuth client, because that is how FSM identifies an extension. Liya keeps the per-person record that SAP asks the backend to keep. Every proposal, refusal and confirmed call writes an audit row (`agent.tool.confirmation` and `agent.tool.call`) that records:

- The person Liya acted for.
- `fsm_user` and `fsm_user_id`: the FSM user.
- `fsm_permission_group` and `fsm_permission_group_id`.
- `fsm_person` and `fsm_person_id`.
- The tool and the outcome.

To see who did what in FSM through Liya, open the **Audit log** and search for `fsm_user` or a person's FSM user name. You can export the result from there.

## What the FSM administrator sets up

### Both modes: limit the OAuth client to what Liya needs

In FSM, open **Admin > Account > Clients** and select the client Liya uses. Its policy group and API permission settings should allow only the following.

| Object | Rights | Needed for |
| --- | --- | --- |
| Service call | Read | Every mode |
| Activity | Read | Every mode |
| Person | Read | Every mode |
| Equipment | Read | Every mode |
| Business partner | Read | Every mode |
| Activity | Update | Dispatching only |
| Service assignment | Create, update and delete | Dispatching only |

Only the FSM company Liya uses needs these rights. Give the client nothing else: no create or delete on service calls or activities, and no other objects. Technician recommendations use FSM's Optimization API, which only computes and changes nothing.

### Mapped mode

1. **Give the OAuth client the account's users and permission groups to read.** Liya reads them with the client's token from FSM's Master Data API:
   - `GET /api/master/v1/accounts/{account}/companies/{company}/users`
   - `GET /api/master/v1/accounts/{account}/groups`

   If FSM refuses either request, Liya tells the person so and sends nothing.
2. **Make each person's FSM user carry their work email.** Use the same address as their Microsoft Entra UPN or email, on exactly one FSM user. In FSM, the email is set under **Admin > Users**. If two FSM users share an address, Liya refuses that person until one of them is changed.
3. **Check the permission groups.** Planners' groups need the planning rights above. Technicians' groups usually read *Own* records only, so mapped identity refuses their reads. Decide whether that is what you want.
4. **Optionally, name the groups** for `dispatch_groups` and `read_groups`.

### In Liya

Set the identity when you add the connection: under **Identity**, choose **mapped**. To change it on an existing connection, send the fields with `PATCH /api/mcp/servers/{name}`:

```bash
curl -X PATCH https://<host>/api/mcp/servers/fsm \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"update_mask": ["identity", "dispatch_groups"],
       "server": {"identity": "mapped", "dispatch_groups": ["Planners"]}}'
```

| Setting | API field | Value |
| --- | --- | --- |
| Identity | `identity` | `shared` (default) or `mapped`. |
| Dispatch groups | `dispatch_groups` | With `mapped`: the FSM permission groups, by id or name, that may plan and dispatch. Blank means any group whose FSM rights allow planning. |
| Read groups | `read_groups` | With `mapped`: the groups that may use the connection at all. The dispatch groups may too. Blank means anyone with an FSM user in the company. |

Mapped identity needs the account's numeric id. Either **Account** is the id, or **Account id** is set.

## What has been tested

On 3 October 2026, the users and permission group listings, and the Person record's user name and email fields, were read on a live FSM tenant. Only their field names and shapes were inspected. Mapping, every refusal, the permission checks and the audit fields are covered by automated tests against a fake FSM built to those shapes.

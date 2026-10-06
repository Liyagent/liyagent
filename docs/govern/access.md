---
title: Access
order: 2
summary: Manage users, roles, role bindings and Cedar policies, start from policy templates, and review access regularly.
outcomes: Add a user with a built-in role; Write a Cedar policy and validate it; Instantiate a policy template for an agent
---

## Users and roles

1. Open **Access** → **Users** and choose **+ Add user**. Pick a role.

   | Role | For |
   | --- | --- |
   | Owner | Everything, including every tenant |
   | Administrator | Everything except managing users and roles, and weakening an active control |
   | Operator | Running the service desk: working tickets, starting and stopping agents, managing sources; builds no agents |
   | Analyst | Reading everything operational, and running assistive agents |
   | Reviewer | Working the review queues they are assigned to, and nothing else |
   | Viewer | Read-only |

2. To create a custom role, open **Roles**, choose **+ Add role**, pick permissions and **Create role** (`PUT /api/access/roles/{name}`).
3. To give a person a role in one tenant, or in every tenant, add a role binding (**Role bindings**, `POST /api/access/role-bindings`). To manage membership in your directory instead, map directory groups to roles on the SSO provider (**Roles from groups**) or provision groups with SCIM; see [Identity and roles](/docs/govern/identity-roles).

## Policies

Policies are written in Cedar and checked on the server: for people's actions in the console and API, and for an agent's own model calls (on the governed LLM path), tool calls (in the managed runtime), token requests and calls to remote agents.

1. On **Access** → **Policies**, choose **+ Create policy**. Set **Effect** (Permit or Forbid), the **Principal**, the action and the resource.
2. Validate before saving: `POST /api/policies/validate`. See what a set of policies means for a principal with `GET /api/policies/effective`.
3. **Save policy**.

```text
forbid (
  principal == TicketIQ::Agent::"hr-helper",
  action == TicketIQ::Action::"call_tool",
  resource in TicketIQ::McpServer::"jira"
);
```

> [!WARNING]
> A forbid always wins over a permit. Use forbids for hard lines, and permits for everything role-based.

## Policy templates

Built-in templates (**Access** → **Templates**) cover common levels of access to an agent: **Read only**, **Sandboxed** (read and run), **Standard** (run, reconfigure and use as a subagent, but not the kill switch) and **Full access**. With the `policy_custom_templates` setting on, you can add your own (**+ New template**): one Cedar statement with a `?principal` and/or `?resource` slot, up to 100 templates.

## Access reviews

`GET /api/access/review` compares what each agent is granted (Cedar policies, credentials, tools, providers) with what it actually used, and lists the gaps as findings. Start a review (`POST /api/access/reviews`), dismiss or act on each finding, and sign it off (`POST /api/access/reviews/{review_id}/signoff`). Sign-off is refused to whoever started the review, and while any high finding is neither fixed nor dismissed.

## Next steps

- [Agent permissions](/docs/govern/permissions)
- [Identity and roles](/docs/govern/identity-roles)

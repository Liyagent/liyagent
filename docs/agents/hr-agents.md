---
title: HR agents
order: 7
summary: Liya HR and Liya Onboarding answer HR questions as the employee (time off, holidays, their profile, onboarding, HR policy). Sensitive matters go to Human Resources.
outcomes: Connect Workday or BambooHR so the HR agents act as each employee; Turn HR on for one client without turning it on for the others; Know what employees see in Teams, and what is never answered by a model; Validate the HR agents with the HR eval set
---

Liya has two HR subagents. Employees just **ask Liya** (in Teams or the web chat) and an HR question is answered by the HR agent, as that employee:

| Agent | Subagent name | What it does |
| --- | --- | --- |
| **Liya HR** (`hr-assist`) | `hr` | Time-off balances and requests, company holidays, pay dates and payslip questions (read-only, from policy), the employee's own profile, and HR policy questions answered with the policy passage cited. |
| **Liya Onboarding** (`hr-onboarding`) | `onboarding` | A new hire's onboarding checklist and what is still open, their first week, their manager and onboarding buddy, and IT requests for access or equipment, filed to the IT Service Desk through the ticket pipeline. |

Both are built-in agents: they are under **Agents › All agents** with Liya, with their own **Settings**, **Playground**, **Transcripts** and **Permissions** tabs, and you can rename them and change their avatar as you can Liya's.

> [!IMPORTANT]
> HR is **off for every client** until an administrator turns it on for that client. An ITSM client that never asked for HR does not have its employees' leave questions answered by an HR agent.

## How they answer

The HR agents answer **rules first** (engine `rules+model`):

1. **Never answered by a model.** A sensitive HR matter (a grievance, harassment, discrimination, a medical condition, a dismissal, a pay dispute) is refused at the input guardrail `hr-sensitive-topics` and filed to the **Human Resources** team as a handoff ticket linking the conversation. The employee is told a person has it. Its transcript is kept as **metadata only**.
2. **Refused.** Another employee's HR data ("How much leave does Nancy have?"), approving time off, and prompt injections (the `hr-block-injection` guardrail, and again in the rules).
3. **Read as the employee.** Balances, requests, holidays and the profile come from the HR system through the agent's HR tools. Each call goes through the governed tool path (Cedar on the server and tool, data policies, write posture, tool-call guardrails) and is audited as `agent.tool.call`. Numbers are the HR system's, never a model's.
4. **Confirmed before it is written.** A time-off request, a profile change or an IT request is prepared and shown on a confirmation card with the exact facts (for example the date "Friday" was read as). Nothing is sent until the employee presses **Confirm** (or types `confirm`), and the HR tool itself refuses a write without that confirmation.
5. **Cited.** Policy, pay-date and payslip questions are answered by quoting the HR policy passage, with its reference.

An HR question the rules cannot place goes to the model bound to the agent, with the policy passages found and the HR tools (whose writes still need the employee's confirmation). With no model bound, the agent says what it can do.

PII an employee pastes (an SSN, a card number) is masked by the `hr-mask-pii` guardrail before the rules, a model or a transcript sees it.

## Acting as the employee

No HR self-service tool takes an employee id. The employee is the **verified requester** of the conversation (the Teams sender the bot looked up in the directory), and the HR system is asked for "me" with **that employee's own credential**:

- The record the HR system returns for "me" must carry one of the requester's own addresses, or the call is refused.
- A server that would read with a company-wide API key is refused: the self-service tools need a **per-user OAuth connection**.
- In a group chat or a channel nothing personal is looked up. The employee is asked to use a 1:1 chat.

## Prerequisites

- The **admin** or **owner** role.
- A Workday or BambooHR tenant, with an OAuth application registered for per-user access, or the synthetic demo (below).
- For Teams: Liya's Teams bot ([Microsoft Teams](/docs/connect/teams)).

## Set up

### 1. Connect the HR system as each employee

1. On **Connections**, register an OAuth provider for your HR system:
   - **Workday**: an API client for integrations using the authorization-code grant, with the Staffing and Absence Management scopes. Workday's REST API accepts a bearer token only.
   - **BambooHR**: BambooHR's OAuth (OpenID Connect) application. Do not use an API key for self-service, because an API key is a company-wide credential.
   - If your employees already sign in to Liyagent and Teams with the same identity provider as the HR system, an **on-behalf-of** provider mints each employee's token from their sign-in with no connect step.
2. On **MCP servers**, add a managed **Workday** or **BambooHR** server and choose **User OAuth** with that provider.
   - Workday: the tenant name, and at least the `staffing` and `absence` services.
   - BambooHR: the company subdomain and, if you track onboarding in BambooHR, the custom table your onboarding tasks live in (`onboarding_table`) and the custom field that names a new hire's buddy (`buddy_field`).
3. On **Liya HR** and **Liya Onboarding** → **Settings** → **Tools**, attach the server and allow only the self-service tools: `my_profile`, `my_time_off_balances`, `my_time_off_requests`, `time_off_types`, `company_holidays`, `my_onboarding`, `request_time_off`, `update_my_profile`. Set **Run as** to **The invoker**, so each call carries the employee's own token. A server on a per-user connection can only be attached to an agent that runs as the invoker.

> [!NOTE]
> A per-user connection is bound to the person the agent runs as. In Teams that means the bot's access mode must match people to Liyagent accounts (**Only people whose Liyagent access allows it**), with single sign-on for on-behalf-of tokens. A Teams sender who is only looked up in the directory can use the synthetic demo but not a real per-user HR connection.

### 2. Give them the HR policies

Ingest your HR handbook into a knowledge collection. Then, on **HR › Setup**, under **Policy library**, choose **Your HR documents**, enter the collection's name and choose **Save library**. **Demo handbook** uses the synthetic Globex policies instead. The library is the instance's, so only an instance owner can set it. **HR › Policies** lets you browse what is loaded.

Each passage should carry `title`, `section` and `ref` so answers can cite it.

### 3. Turn HR on for a client

On **HR › Setup**, under **Liya HR and Liya Onboarding**, switch each agent on. The same switches are under **hr** and **onboarding** in Liya's **Settings → Subagents**. A switch applies to the client you are working in only. With the API:

```bash
curl -X PUT https://<host>/api/agents/copilot/subagents/hr/tenant-state \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"on": true}'
curl -X PUT https://<host>/api/agents/copilot/subagents/onboarding/tenant-state \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"on": true}'
```

Each switch is audited as `agent.subagent.tenant_state`.

**HR › Setup** also shows the HR system each agent reads, the HR guardrail pack, and **Onboarding IT handoff**: where a new hire's confirmed IT request goes (**IT service desk**, an **ITSM connection** such as ServiceNow, Jira, Zendesk or Freshservice, **Email**, or **Not set up**).

### 4. Decide whether HR approves writes too

The employee's confirmation is always required. Whether a person in HR must approve the write as well is the HR server's write posture, on its **MCP servers** page:

- A server you add now starts at **Require approval** for writes, so a confirmed time-off request or profile change waits in the **Inbox** under **Approvals** before it is sent.
- To send confirmed requests straight to the HR system, set the posture for `request_time_off` and `update_my_profile` (or the server's default for writes) to **Allow**.

## In Teams

Employees ask Liya in a 1:1 chat:

| They say | They get |
| --- | --- |
| "How much leave do I have left?" | Their balances by type, from the HR system. |
| "Book Friday off" | A confirmation card with the exact date. **Confirm** files it as *requested* for their manager to approve in the HR system. |
| "What's the parental leave policy?" | The policy passage, quoted, with its reference and a citation. |
| "Who is my onboarding buddy?" | Their manager and buddy from the HR record. |
| "I need access to the test lab VPN" (new hire) | A confirmation card. **Confirm** files an IT Service Desk ticket. |
| "I want to report harassment" | "I've passed it to the Human Resources team", and a person follows up. |
| "How much leave does Nancy have?" | A refusal: they can only see their own records. |

Every routing is Liya's delegation to the HR agent, checked by Cedar `delegate` and audited as `agent.subagent.call`. A forbid keeps the message with Liya.

## Try it with the synthetic demo

Set `TICKETIQ_HR_DEMO=true` (and `TICKETIQ_HR_DEMO_TENANT` for a client other than the default). At startup this:

- registers `hr-demo`, an in-process, **BambooHR-compatible** HR system for **Globex Industries**, a fictional company, and attaches it to both HR agents with the self-service tools only.
- makes the synthetic HR handbook (leave, parental leave, holidays, expenses, code of conduct, pay, onboarding) their policy source, and loads it into its own vector collection.
- switches HR on for the demo client only.
- seeds the `hr-agents` eval set.

Everything in it is invented. Its employees are the demo's synthetic requesters, such as `richard.haddad@globex-industries.com`, so a Teams demo identity lines up with an HR record.

## Validate

The `hr-agents` eval set holds 41 cases (balances, requests with confirmation, policy with citations, other-employee refusal, sensitive-topic escalation, prompt injection, PII masking, off-topic and onboarding), each asked as a named synthetic employee. Run it against the synthetic demo:

```bash
python -m ticketiq.evalrun --dataset hr-agents --agent hr-assist
```

or from the **Evaluations** page. A case can also say what the answer must **not** contain (`expect.excludes`), which is how a leak of another employee's data or of a masked value fails the case.

## What has not been validated

The HR agents are validated end to end against the synthetic BambooHR-compatible system only. The Workday and BambooHR self-service calls follow each vendor's public API documentation and have not been run against a real customer tenant, so spot-check them against yours before relying on them. Greenhouse (recruiting) is not part of the HR agents.

## Next steps

- [Sub-agents](/docs/agents/sub-agents)
- [MCP servers](/docs/connect/mcp-servers)
- [Microsoft Teams](/docs/connect/teams)
- [Playground and evals](/docs/agents/playground-evals)

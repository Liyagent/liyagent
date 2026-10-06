---
title: How Liya confirms SAP calls
nav_title: SAP confirmations
order: 13
summary: Which SAP calls show a Confirm card in Teams, which run straight away, and why each stays inside SAP's API Policy.
outcomes: Tell which SAP calls wait for a Confirm card and which run on a click; Set a connection to the SAP Integration Suite MCP Gateway route; Read the audit rows and timings for an SAP turn
---

Liya asks you to confirm an SAP call only when the policy or a change to your data calls for it. This page shows when you see a card, and why.

> [!NOTE]
> This page describes how Liya behaves. It is not legal advice. You remain responsible for your SAP licensing and for how you use SAP's APIs.

## What runs, and what waits

| What starts the call | Direct connection (S/4HANA, SuccessFactors, Field Service Management, SAP product) | SAP Integration Suite MCP Gateway route |
| --- | --- | --- |
| The agent decides to **read** | One Confirm card | Runs, no card |
| The agent decides to **write** | One Confirm card | One Confirm card |
| You click a **read** button under a result, or send a starter prompt | Runs, no card | Runs, no card |
| You click a **write** button under a result | One Confirm card | One Confirm card |
| A schedule, trigger, group chat or another app | Refused | Reads run; writes are refused |
| A read routine you set up and confirmed in Teams | Runs the confirmed read, no card | Not offered: routines run only through Liya's own SAP connectors |
| A routine whose call writes | One Confirm card on each run | Not offered |

If the agent proposes several calls in one turn, they all go on **one** card with **Confirm all**, under a single short line. Typing `confirm` or `cancel` answers the whole card. A card holds at most five calls. Liya cancels any extra calls, so nothing waits that you never saw.

## Why this stays inside SAP's API Policy

SAP's API Policy (v.4.2026a), section 2.2.2, restricts AI systems that plan, select or execute sequences of SAP API calls to the routes SAP endorses. One of those routes is the MCP Gateway in SAP Integration Suite. Two FAQ answers (v1.3) also apply here:

- **Q40**: pre-defined, deterministic call sequences with no AI decision-making are outside that clause.
- **Q56**: a custom connector may be used if every rule is kept.

Liya applies the policy as follows:

- **A direct connection is not an endorsed route.** So when the agent picks an SAP call, nothing reaches SAP until you confirm that exact call. It then runs once, as fixed code. This applies to reads and writes alike.
- **A button is your choice, not the agent's.** After a result, Liya's own code (not a model) turns the next steps into buttons. Each button carries the exact tool and arguments, and its title says what will run. When you click a read button, the call runs as your own call. No model chooses or changes it, which is the deterministic, person-decided case in Q40. A write button still shows one Confirm card, because it changes SAP data.
- **Starter prompts** (such as *Open service calls ready to plan*) work the same way when you send them word for word. Each one maps to one fixed read.
- **The gateway route is endorsed.** Section 2.2.2 names the MCP Gateway as an allowed route. So on a connection set to that route, the agent's reads run without a card. Writes still wait for your Confirm, because they change data in SAP.

### How buttons are protected

A button's payload is signed with HMAC-SHA256, using a key derived for this purpose alone. The payload is bound to you, to the assistant and to the connection, and it expires after two hours. Liya runs nothing when:

- the button was forged or altered;
- the button has expired; you see *that button has expired — ask again*;
- the button was made for someone else, or for another assistant.

When you click, Liya looks up again whether the call reads or writes. It uses the connector's own catalogue, or the gateway server's pinned tool hints, and never trusts the button's payload for this.

## Set a connection to the MCP Gateway route

1. Deploy and publish the MCP server in SAP Integration Suite. See [Connect through your SAP Integration Suite MCP Gateway](/docs/connect/sap#connect-through-your-sap-integration-suite-mcp-gateway).
2. Add it in Liya with the **SAP MCP Gateway** card. Use transport **streamable-http** and OAuth client credentials. The card ticks **SAP Integration Suite MCP Gateway** for you. Through the API, set `"sap_route": "sap_mcp_gateway"`.
3. [Pin the server's tools](/docs/connect/mcp-servers#keep-tools-stable). Liya treats a tool as a read only when its pinned hints say `readOnlyHint: true` and do not say `destructiveHint: true`. Every other tool, including any tool that isn't pinned, waits for a Confirm.

Only a streamable-http server can take this route. A direct SAP connector is always `direct`, and Liya refuses `sap_route: "sap_mcp_gateway"` on it. To act with no person behind a call, such as a scheduled agent that writes, register the gateway server without `sap_route`. It then works like any other remote MCP server.

## What the audit log shows

| Row | When |
| --- | --- |
| `agent.tool.confirmation` with `outcome: proposed` | The agent proposed a call |
| `agent.tool.confirmation` with `outcome: person_named` | You clicked a button or sent a starter. `source` is `button` or `starter`. |
| `agent.tool.call` with `via: sap-person` | A read you named ran as your call |
| `agent.tool.call` with `via: sap-confirmed` | A call ran after you confirmed it |
| `agent.tool.confirmation` with `outcome: routine` | A scheduled routine's read was let through. `routine` names the routine. |
| `agent.tool.call` with `via: sap-routine` | A routine's read ran |
| `teams.sap_button` | A button was checked: `run`, `proposed` or `refused` |
| `teams.sap_confirm` | The result reached you. `timings` gives `execute_ms` (SAP), `phrase_ms` (the answer) and `total_ms`. |
| `teams.message` | An SAP turn. `timings` gives `agent_ms`, `reply_ms` and `turn_ms`. |

## Faster follow-ups

When an agent has more tools than its `deferred_tools_threshold`, its first step searches for the right tool (`find_tools`). Liya now remembers which tools a conversation already found, for four hours. The next turn starts with those tools loaded and skips the search. The tools still pass every check they would pass if found again.

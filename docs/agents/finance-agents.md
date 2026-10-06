---
title: Finance agents
order: 8
summary: Liya Finance checks vendor invoices against their purchase orders in NetSuite or Dynamics 365 Finance, lists the invoices that differ beyond your tolerance, holds an invoice for AP review once a person approves, and answers spend questions from Ramp.
outcomes: Connect NetSuite, Dynamics 365 or Ramp so Liya Finance acts as each person; Turn Finance on for one client without turning it on for the others; Set the tolerance invoices are matched with; Know what Liya Finance never does
---

Liya has a finance subagent. People **ask Liya** — in Teams or the web chat — and an accounts-payable or spend question is answered by **Liya Finance**, as that person:

| Agent | Subagent name | What it does |
| --- | --- | --- |
| **Liya Finance** (`liya-finance`) | `finance` | Matches a vendor invoice to its purchase order line by line, lists open invoices that need a person, holds an invoice for AP review (after a person approves the hold), and totals card spend by vendor, department or period. |

Liya Finance is under **Agents › All agents** with its own **Settings**, **Playground**, **Transcripts** and **Permissions** tabs. The **Finance** app in the rail has two tabs: **Overview** and **Setup**.

> [!IMPORTANT]
> Liya Finance never approves, pays, releases or deletes an invoice. Holding an invoice is the only change it can ask for, and every hold waits for a person's approval in the **Inbox**.

## Tools

Each tool is on the connector it reads. Reads run as asked. Writes are held for approval.

| Connector | Tool | Read or write |
| --- | --- | --- |
| NetSuite | `match_vendor_bill` — one vendor bill against its purchase order | Read |
| NetSuite | `list_bill_variances` — open and pending-approval bills that need a person | Read |
| NetSuite | `hold_vendor_bill` — sets the bill's **Payment Hold**, and optionally its approval status back to **Pending Approval** | Write, held for approval |
| Dynamics 365 | `match_vendor_invoice` — one vendor invoice against its purchase order | Read |
| Dynamics 365 | `list_invoice_variances` — pending vendor invoices that need a person | Read |
| Dynamics 365 | `hold_vendor_invoice` — sets the invoice header's on-hold column | Write, held for approval |
| Ramp | `spend_summary` — card spend by vendor, department or period (month, quarter or ISO week) | Read |

The hold tools wait for a person whatever the server's **Agent writes** setting says. They also need a reason, which the approver sees.

## How a match is judged

Each invoice line is paired with the order line it bills. Liya Finance pairs by the order line the ERP names on the invoice line first, then by item, then by description. Then, for each line:

- **Quantity.** Billing more than was ordered is a variance. Where the order records receipts, billing more than was received is a variance too (a three-way match). Billing less than was ordered is a partial invoice, not a variance. Order lines that were not billed are listed as **not invoiced**.
- **Unit price.** The invoice's unit price is compared with the order's, valued over the quantity billed.
- **Line amount.** A line amount that is not quantity × price is a variance. A difference of one cent or less is rounding.
- **Not on the order.** A line that bills something the order does not carry is always a variance.

For the whole invoice, the line total is compared with what those lines should cost at the order's prices. Tax and charges on the header are shown as **charges** and are not judged.

An invoice with **no purchase order**, or in a **different currency** from its order, is flagged for a person. Amounts in two currencies are never compared or added.

Amounts are exact decimals, rounded half up to the cent, and are always given with their currency, for example `USD 1,050.00`.

## The tolerance

A difference is within tolerance when its value is no more than the allowance on the value it is measured against:

- a **percentage** of that value (the default is **2%**),
- a fixed **amount** in the invoice's currency, or
- both, and then **whichever is less**.

A difference exactly at the allowance is within it. The tolerance belongs to the client. Set it on **Finance › Setup** under **Match tolerance**, or with the API:

```bash
curl -X PUT https://<host>/api/finance/tolerance \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"pct": 2, "amount": 50}'
```

Each change is audited as `finance.tolerance.update`.

## Prerequisites

- The **admin** or **owner** role.
- Finance turned on for the client (it is on wherever no solution row restricts it).
- A NetSuite account, a Dynamics 365 Finance environment, or a Ramp business, each with an OAuth application for per-user access.

## Set up

### 1. Connect a finance system as each person

1. On **Connections**, register an OAuth provider for the system. The callback URL is shown on **Finance › Setup**.
   - **NetSuite**: an integration record with OAuth 2.0 authorization code grant and the REST web services scope. The person's NetSuite role decides what they can read and hold.
   - **Dynamics 365**: a Microsoft Entra app registration with delegated access to Dataverse.
   - **Ramp**: a Ramp developer app with the transactions read scope.
2. On **MCP servers**, add a managed **NetSuite**, **Dynamics 365** or **Ramp** server with that connection. Each person then connects their own account; Liyagent never holds a shared finance credential.

### 2. Attach it to Liya Finance

On **Finance › Setup**, under **Liya Finance**, choose **Attach to Liya Finance** next to the server. This:

- adds the server to Liya Finance's tools;
- turns Liya's `finance` subagent **on for the client you are working in only**.

Liya Finance runs as **the invoker**, so each call carries the person's own token. Each attach is audited as `finance.agent.attach`. The same on/off switch is under **finance** in Liya's **Settings → Subagents**.

### 3. Set the tolerance

On **Finance › Setup**, under **Match tolerance**, enter a percentage, an amount, or both, and choose **Save tolerance**.

### 4. Dynamics 365: check the table names

Liya Finance reads Dynamics 365 Finance's accounts-payable data entities through Dataverse virtual tables (the `mserp_` tables for vendor invoice headers and lines and purchase order headers and lines). If your environment names a table or column differently, set `finance_fields` on the Dynamics 365 server through the MCP servers API, for example `{"invoice_hold": "cr_onhold"}`. Only the names Liya Finance knows are accepted.

## In Teams

People ask Liya in a chat:

| They say | They get |
| --- | --- |
| "Does bill 4512 match its PO?" | The match, line by line, with every difference and whether it is within tolerance. |
| "Which open invoices are off from their POs?" | The invoices that differ beyond tolerance, have no order, or are in another currency. |
| "Hold bill 4512 — the price is 3% over." | A hold request waiting in the **Inbox**. Liya Finance says it is waiting for approval. |
| "What did Engineering spend on cards last quarter?" | Spend totals by department, per currency. |
| "Pay bill 4512." | A refusal: a person pays invoices in the finance system. |

## The Finance app

- **Overview** (`/finance`) shows the invoices checked and the variances found this week, the holds waiting for approval, the finance systems and how many people have connected, the agents' calls by tool and recent errors.
- **Setup** (`/finance-setup`, administrators) shows the callback URL, the finance systems, Liya Finance and the match tolerance.
- **Home** shows a Finance card with the same week's numbers.

## What has not been validated

Liya Finance's matching is tested case by case against synthetic data. The NetSuite, Dynamics 365 and Ramp calls follow each vendor's public API documentation and have not been run against a real customer tenant:

- **NetSuite**: the vendor bill and purchase order records with sublists expanded, SuiteQL status codes for open (`A`) and pending-approval (`D`) bills, and the `paymentHold` and `approvalStatus` fields.
- **Dynamics 365**: the default virtual table and column names, including the on-hold column. Check them against your environment and override them with `finance_fields`.
- **Ramp**: the transaction fields used for spend (`amount`, `currency_code`, `merchant_name`, the card holder's department) and the `page.next` cursor.

Spot-check against your own tenant before relying on them.

## Next steps

- [Sub-agents](/docs/agents/sub-agents)
- [MCP servers](/docs/connect/mcp-servers)
- [Microsoft Teams](/docs/connect/teams)
- [Playground and evals](/docs/agents/playground-evals)

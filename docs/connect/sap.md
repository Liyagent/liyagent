---
title: Connect SAP
nav_title: SAP
order: 10
summary: Connect Liya to SAP S/4HANA's and SAP SuccessFactors' own APIs, with a person confirming each agent call, or through the MCP Gateway in your SAP Integration Suite.
outcomes: Choose between a direct connection and your SAP Integration Suite MCP Gateway; Add an SAP S/4HANA connection for the business areas you use; Add a read-only SAP SuccessFactors connection; Explain how a direct connection keeps every agent call to SAP with the person who asked; Add an MCP server from SAP Integration Suite with the SAP MCP Gateway card
---

Liya reaches SAP in one of two ways.

| | Directly to SAP's APIs | Through your SAP Integration Suite MCP Gateway |
| --- | --- | --- |
| Use it when | You don't have SAP Integration Suite | You have SAP Integration Suite |
| In Liyagent | The managed **SAP S/4HANA** and **SAP SuccessFactors** servers | The **SAP MCP Gateway** card: a remote MCP server |
| What agents get | Fixed tools over SAP's published S/4HANA APIs, by business area | The tools you publish on the gateway |
| An agent's call to SAP | Runs only after the person who asked confirms it | Reads run straight away, but writes wait for the person's Confirm (with the gateway route set) |
| Work with no person behind it, such as a schedule | Refused, except a read routine the person set up and confirmed in Teams | Reads allowed. For writes, register the server without the gateway route |

Liyagent also runs managed **SAP Field Service Management** servers (see [SAP Field Service Management](/docs/connect/sap-fsm)) and **SAP Products** servers, which reach a chosen SAP product's APIs. An agent's calls to SAP through either are confirmed the same way as on a direct S/4HANA connection.

## Connect directly to SAP S/4HANA

Liyagent runs the managed **SAP S/4HANA** server itself. You give it your system's address and a communication user, and it calls SAP's published OData APIs, V2 and V4 alike. It offers fixed tools only. No tool takes a free-form query, so an agent can't compose its own request to SAP.

Every SAP call an agent makes on this connection waits for the person who asked to confirm it. See [Working within SAP's API Policy](#working-within-saps-api-policy).

### Prerequisites

- An S/4HANA system that Liya can reach over HTTPS: S/4HANA Cloud, or an on-premise or private cloud system.
- A communication user: the inbound user of a communication arrangement that exposes the APIs of the business areas you use. It is a technical user, not a person's login.
- A Microsoft Teams bot, Google Chat app or web chat for the agent, where people confirm the calls it proposes. See [Microsoft Teams app](/docs/connect/teams) and [Google Chat](/docs/connect/google-chat).

### Business areas and tools

A connection offers the tools of the business areas you switch on. SAP licenses its APIs area by area, and each area needs a communication arrangement in your SAP system that exposes its APIs. With no areas set, a connection offers `maintenance` and `purchasing`.

| Area | Covers | SAP APIs it needs |
| --- | --- | --- |
| `maintenance` | Equipment, functional locations, maintenance notifications and orders, measuring points and their readings | `API_EQUIPMENT`, `API_FUNCTIONALLOCATION`, `API_MAINTNOTIFICATION`, `API_MAINTENANCEORDER`, and the OData V4 services `api_measuringpoint` and `api_measurementdocument` |
| `purchasing` | Purchase orders and purchase requisitions | `API_PURCHASEORDER_PROCESS_SRV`, `API_PURCHASEREQ_PROCESS_SRV` |
| `sales` | Sales orders, outbound deliveries and billing documents | `API_SALES_ORDER_SRV`, `API_OUTBOUND_DELIVERY_SRV` (version 0002), `API_BILLING_DOCUMENT_SRV` |
| `inventory` | Stock by material, plant and storage location | `API_MATERIAL_STOCK_SRV` |
| `finance` | Supplier invoices and cost centres | `API_SUPPLIERINVOICE_PROCESS_SRV`, `API_COSTCENTER_SRV` |
| `master_data` | Business partners and products | `API_BUSINESS_PARTNER`, `API_PRODUCT_SRV` |

Each area offers these tools:

| Area | Tool | What it does |
| --- | --- | --- |
| Maintenance | `search_equipment` | Finds equipment by id or name, plant or functional location. Current records only. |
| | `get_equipment` | One equipment's master data. |
| | `find_functional_location` | Finds functional locations by id or name, optionally in one plant. |
| | `list_notifications` | Maintenance notifications for an equipment or functional location, open ones by default. |
| | `get_notification` | One maintenance notification. |
| | `create_notification` | **Creates** a maintenance notification. SAP limits the short text to 40 characters, so the rest goes into the long text. A ticket id links it back to the ticket. |
| | `list_work_orders` | Maintenance orders for an equipment, location, order type or notification, open ones by default. |
| | `get_work_order` | One maintenance order with its operations. |
| | `create_work_order` | **Creates** a maintenance order, optionally from a notification. |
| | `list_measuring_points` | The measuring points of an equipment or location, with their SAP limits. |
| | `get_measurement_readings` | Recent readings of one measuring point, newest first. |
| | `analyze_equipment_health` | Predictive maintenance for one equipment, described below. |
| | `raise_predicted_failure` | **Creates** one maintenance notification with the evidence when an equipment is heading for a limit. With `dry_run`, it shows the notification without creating it. |
| Purchasing | `search_purchase_orders` | Purchase orders by supplier, purchasing group or date. For a material, its open purchase order items. |
| | `get_purchase_order` | One purchase order with its items and delivery dates. |
| | `create_purchase_requisition` | **Creates** a purchase requisition of up to 20 items. It enters SAP's release workflow. Nothing is ordered or approved. |
| Sales | `search_sales_orders` | Sales orders for a customer or the customer's own PO reference, open ones by default. |
| | `get_sales_order` | One sales order with its items and the deliveries made against it. |
| | `get_delivery` | One outbound delivery: goods issue, picking and proof of delivery. |
| | `get_billing_document` | One billing document: its amounts, and whether it is cancelled or posted to accounting. |
| Inventory | `check_stock` | Stock of a material by plant and storage location, with a total per plant. |
| Finance | `search_supplier_invoices` | Supplier invoices, with whether payment is blocked, whether the invoice was reversed, and its net due date. |
| | `get_supplier_invoice` | One supplier invoice, by number and fiscal year. |
| | `get_cost_center` | A cost centre's current record: its name, the person responsible, company code and profit centre. |
| Master data | `find_business_partner` | Customers and suppliers by number or name. Identifying fields only: no addresses, contacts or bank details. |
| | `find_product` | Products by number or by words in their name. |

The four tools that create documents work only once document creation is switched on. See [Documents and SAP Digital Access](#documents-and-sap-digital-access). Releasing or approving a purchase requisition or order is not offered: those commit money and stay in SAP's own approval workflow.

**Predictive maintenance.** `analyze_equipment_health` trends each measuring point of an equipment from its SAP measurement documents, and projects when it will cross the limits set on that point in SAP. `raise_predicted_failure` then raises one maintenance notification with the evidence, and no second one while the first is still open.

### Add the connection

1. Open **MCP servers**, choose **Add MCP server**, and pick **SAP S/4HANA** in the catalogue.
2. Enter a name for the server, such as `s4`.
3. Fill in the SAP settings. All are optional except the API host, which the sandbox doesn't need.

   | Setting | API field | Value |
   | --- | --- | --- |
   | S/4HANA API host | `base_url` | For S/4HANA Cloud, the `-api` host, such as `https://my123456-api.s4hana.cloud.sap`. |
   | Environment | `environment` | Blank for your own system, or `sandbox` for [SAP's sandbox](#try-it-against-saps-sandbox). |
   | Default planning plant | `maintenance_plant` | Used by new notifications, orders and requisitions, such as `1010`. |
   | Default main work center | `main_work_center` | Used by new maintenance orders, such as `RES-0100`. |
   | Default purchasing group | `purchasing_group` | Used by new requisitions, such as `001`. |
   | SAP client | `sap_client` | Three digits, such as `100`. Only for on-premise or private cloud. S/4HANA Cloud ignores it. |
   | Let Liya create SAP documents | `digital_access_ack` | Off by default, so the connection only reads. See [Documents and SAP Digital Access](#documents-and-sap-digital-access). |
   | Calls a minute | `max_calls_per_minute` | Calls a minute to this SAP system from each Liya process, from 1 to 600. Blank is 60. |
   | Business areas | `sap_areas` | Comma-separated: `maintenance`, `purchasing`, `sales`, `inventory`, `finance`, `master_data`. Blank is `maintenance` and `purchasing`. |
   | Language | `language` | The SAP language key that texts are read in, such as `DE`. It applies to cost centre and product names. Blank is English. |

4. Under **Auth**, choose how the connection signs in to SAP.

   | Auth option | Use for | What it takes |
   | --- | --- | --- |
   | **Communication user** | Your own SAP system | The communication user's name and password (`SAP_USERNAME` and `SAP_PASSWORD` in `env`) |
   | **Sandbox API key** | SAP's sandbox only | Your API key from api.sap.com (`SAP_API_KEY` in `env`) |
   | **User OAuth** | Calls made with each person's own delegated token | A [connection provider](/docs/connect/connections#register-a-provider-admin) for your SAP system (`connection`) |

   For the password or the key, type the label of a secret you stored, or paste the value. The form stores a pasted value in the [secrets store](/docs/connect/secrets) as `<name>-password` or `<name>-api-key`, and the server keeps only its `secret://` reference.

5. Optionally, narrow what agents see: list tools in **Exposed tools**, or tick **Read-only** to hide every tool that creates something.
6. Choose **Save server**, then grant the server to an agent on the agent's **Settings** tab.
7. Try a tool yourself: choose **Inspect** on the server's row, pick a tool and choose **Run tool**. Your own call runs at once.

### Change a connection later

The console has no **Edit** view for managed servers. To change a setting, send that field with `PATCH /api/mcp/servers/{name}` and an `update_mask`. For example, to switch on document creation:

```bash
curl -X PATCH https://<host>/api/mcp/servers/s4 \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"update_mask": ["digital_access_ack"], "server": {"digital_access_ack": true}}'
```

To change the password, update its secret on **Secrets store**. The server keeps the same `secret://` reference.

## Connect SAP SuccessFactors

Liyagent also runs a managed **SAP SuccessFactors** server, over SuccessFactors' OData V2 API. It only reads: nothing is created, changed or approved in SuccessFactors. Requesting time off, hiring and changing a record stay in SuccessFactors' own workflows.

| Tool | What it does |
| --- | --- |
| `find_employee` | Finds active employees by name, work email or user id, with their title, department, division and location. |
| `get_employee` | One employee's directory record and current job: job title, department, location, company, manager and employment status. |
| `my_time_off` | The asking employee's own absences: type, dates, approval status and amount, from the last 90 days onward (or `days`), upcoming time off included. |
| `my_time_accounts` | The asking employee's own time accounts that can still be booked against, such as annual leave, each with its balance. |
| `list_job_requisitions` | Job requisitions, newest first: title, status, department, location and openings. Deleted ones are left out. |
| `find_department` | Active departments, with each one's parent department, cost centre and head of unit. |
| `find_location` | Active locations, with each one's time zone and location group. |

A SuccessFactors user record also holds pay, national ID, date of birth and home address. Every request Liya sends names the fields it reads, so none of those are ever asked for. When it reads a related record, such as an employee's manager, it names that record's fields too.

**Whose time off.** `my_time_off` and `my_time_accounts` are off on a new connection: an administrator switches them on with **Let employees ask for their own time off** (`self_service`). They answer only for the person who asked. Liya matches the requester's verified email address to exactly one active SuccessFactors user, refuses the call if it can't, and returns only that user's records, whatever the arguments say and whatever SuccessFactors sends back. The connection reads with its technical user: signing in to SuccessFactors as each person (OAuth with a SAML bearer assertion, or OIDC through SAP Cloud Identity Services) is not built yet.

To add the connection:

1. Open **MCP servers**, choose **Add MCP server**, and pick **SAP SuccessFactors** in the catalogue.
2. Fill in the settings.

   | Setting | API field | Value |
   | --- | --- | --- |
   | API server | `base_url` | Your data centre's API host, without `/odata/v2`, such as `https://api4.successfactors.com`. |
   | Environment | `environment` | Blank for your own tenant, or `sandbox` for SAP's sandbox. |
   | Calls a minute | `max_calls_per_minute` | Calls a minute to this tenant from each Liya process. Blank is 60. |

3. Under **Auth**, choose **Technical user**: an API user written `username@companyId`, with its password (`SUCCESSFACTORS_USERNAME` and `SUCCESSFACTORS_PASSWORD` in `env`). Give it permission to read only the employee, time off and recruiting data you want. For the sandbox, choose **Sandbox API key** instead.
4. Choose **Save server**, then grant the server to an agent.

SAP is retiring Basic authentication for SuccessFactors APIs, so OAuth is the next step for this connector. An agent's calls to SuccessFactors follow the same rule as S/4HANA: each one waits for the person who asked to confirm it.

## Connect through your SAP Integration Suite MCP Gateway

With SAP Integration Suite, you publish SAP APIs as MCP servers on its MCP Gateway. Liya connects to each one as a remote MCP server, over Streamable HTTP, with OAuth client credentials. SAP endorses this route for AI agents. With the **SAP Integration Suite MCP Gateway** setting on (`sap_route: "sap_mcp_gateway"`, which the card sets), an agent's reads run without a Confirm card, and anything that can change SAP still waits for one. See [How Liya confirms SAP calls](/docs/connect/sap-confirmations). The gateway's controls apply, and so do Liya's usual controls for a remote server.

### In SAP Integration Suite

At a high level, you build the MCP server, deploy it and publish it. SAP's tutorial [Create an MCP Server for Enterprise AI Agents](https://developers.sap.com/tutorials/integration-suite-mcp-server) has the details.

1. In **Design** → **Integrations and APIs**, open an integration package and choose **Add** → **MCP Server**.
2. As the source, choose **HTTP Endpoint with OpenAPI Specification**. Give the API's URL and import its OpenAPI specification.
3. Choose the API operations to offer as tools.
4. Deploy the MCP server to the **Integration Cell** runtime.
5. Publish it through **Developer Hub**. Note the MCP server's URL, and the **Token URL**, **Key** and **Secret** you get for it. The key is the OAuth client ID.

### In Liyagent

1. Open **MCP servers**, choose **Add MCP server**, and pick **SAP MCP Gateway** in the catalogue. The form opens on **streamable-http** with **OAuth client credentials** chosen.
2. Enter a name and the MCP server's URL. Add one server for each MCP server you deploy.
3. Fill in the server credential.

   | Field | Value |
   | --- | --- |
   | Token URL | The **Token URL** from Developer Hub |
   | Client ID | The **Key** from Developer Hub |
   | Secret | A stored secret's label or `secret://<label>`. Or paste the **Secret**: it is stored in the secrets store as `<name>-auth`. |
   | Scope | Blank, unless your token endpoint needs one |
   | Client authentication | HTTP Basic, the standard, unless your token endpoint wants the client ID and secret in the form body |

4. Choose **Save server**. Liya gets a token with these credentials and renews it before it expires.
5. [Pin the server's tools](/docs/connect/mcp-servers#keep-tools-stable), so a change on the SAP side is flagged, then grant the server to an agent.

The same server through the API, with the secret stored first:

```bash
curl -X POST https://<host>/api/mcp/servers \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "sap-gateway", "transport": "streamable-http", "url": "<MCP server URL>",
       "auth": {"mode": "client_credentials", "token_url": "<Token URL>",
                "client_id": "<Key>", "secret_ref": "secret://sap-gateway-secret"}}'
```

## Working within SAP's API Policy

> [!NOTE]
> This section describes how Liya behaves. It is not legal advice. You remain responsible for your SAP licensing, including SAP Digital Access, and for how you use SAP's APIs.

SAP's API Policy (v.4.2026a, section 2.2.2) restricts AI systems that plan, select or execute sequences of SAP API calls to routes SAP endorses: the MCP Gateway in SAP Integration Suite, SAP's own MCP servers in Joule Studio, and agent-to-agent (A2A) connections through SAP's Agent Gateway. A direct connection is not one of these routes. So on a direct connection, an agent never calls SAP itself.

### An agent proposes, the person confirms

1. **The agent proposes.** An agent's call to an SAP tool sends nothing to SAP. Liya checks the arguments, describes the call in one sentence with the facts it uses, and holds it for the person who asked. The agent is told that the call is waiting.
2. **The person decides.** In Teams, they get a card titled **Run this in SAP?** with the sentence, the facts, and **Confirm** and **Cancel** buttons. In the web chat, the answer ends with the sentence and the same two buttons. Typing `confirm` or `cancel` works in both.
3. **Fixed code runs the call once.** On **Confirm**, the connector's own code runs that one tool, with exactly the arguments the proposal described. The agent then answers from the result with no tools, so it can't chain a second SAP call. A follow-up is a new proposal.

Each proposal is held to these rules:

- Only the person who asked can confirm it.
- It expires after 15 minutes.
- A confirmation runs only the call it was given for, and only once.
- Arguments the call would refuse, such as a malformed SAP id, are refused before anyone is asked. A tool outside the connection's business areas is never proposed.

### When there is nobody to confirm

A person can confirm only in a one-to-one chat with the agent in Microsoft Teams or Google Chat, in the web chat, or in the agent's **Playground** tab when they are signed in to the console. Anything else is refused with a sentence that says why, and nothing is sent to SAP. That includes:

- schedules, webhooks and other triggers
- Teams group chats and channels
- eval runs
- apps and agents that call in through the `/mcp` endpoint or A2A.

Three kinds of call go straight through, because a person has already decided them:

- your own call from the server's inspector (**Run tool**), where you choose the tool and its arguments.
- a call an approver runs from **Approvals**. Approvers only ever see calls the person already confirmed.
- a scheduled routine's read. A person sets up a routine in their Teams chat and confirms one card naming the exact tool, its arguments and when it runs. The scheduler then runs exactly that read, and only while the routine is active. A routine never writes on its own: a write is sent to the person as a new proposal on each run.

### Documents and SAP Digital Access

Documents created in SAP through another system, such as Liya, may count toward your SAP Digital Access licence. So a direct connection creates no documents until an administrator switches on **Let Liya create SAP documents** (`digital_access_ack`). Until then, a call that would create one is refused before anyone is asked to confirm it.

- In Teams, the card names the Digital Access document type the call creates and says it may count toward your licence. A notification or an order is a service and maintenance document. A requisition is a purchase document (per item). The web chat shows the licence note without the type.
- A confirmed write then follows the server's **Agent writes** setting. With **Require approval**, the default for a new server, it waits on **Approvals** until an approver runs it, and the person is told so.
- Liya counts the documents it creates through each connection, per month and document type. **MCP servers** shows this month's count under the server, or that creating documents is off. The server's API record carries it as `sap_documents`.
- The [audit log](/docs/monitor/audit-log) records every proposal as `agent.tool.confirmation`, and every confirmed call as `agent.tool.call`.

### Other safeguards

- Liya calls only SAP's published APIs, through fixed tools. No tool takes a free-form query.
- Each SAP system has a calls-a-minute allowance: 60 unless you set one, counted per Liya process. A call waits up to 10 seconds for room, then is refused.
- Results are read in bounded pages, and a next-page link is followed only on your SAP host.
- Every request says it comes from Liya, with `User-Agent: Liyagent-SAP-Connector/1.0 (+https://liyagent.com)`. Your SAP team, and SAP, can tell Liya's traffic from anyone else's.

For agents that should read without a person confirming each call, use the [Integration Suite MCP Gateway](#connect-through-your-sap-integration-suite-mcp-gateway) instead. Next-step buttons and starter prompts that read run on a click on either route. See [How Liya confirms SAP calls](/docs/connect/sap-confirmations).

## Try it against SAP's sandbox

SAP's public API sandbox serves S/4HANA Cloud's real APIs over SAP's sample data. It accepts reads only, so a call that would create a document is refused.

1. Sign in to api.sap.com and copy your personal API key from your profile (**Show API Key**).
2. Add an **SAP S/4HANA** server. Leave the API host blank and set the environment to `sandbox`. Liya then calls `https://sandbox.api.sap.com/s4hanacloud`.
3. Under **Auth**, choose **Sandbox API key** and paste the key. The form stores it in the secrets store as `<name>-api-key`.
4. To see every tool, list all six business areas: `maintenance, purchasing, sales, inventory, finance, master_data`.
5. Choose **Save server**, then try tools from **Inspect** with **Run tool**.

An agent's calls to the sandbox still wait for confirmation in a chat or the Playground.

The same key works for SuccessFactors: add an **SAP SuccessFactors** server with the environment set to `sandbox`, and Liya calls `https://sandbox.api.sap.com/successfactors`, SAP's sample company.

## What has been tested

Every S/4HANA read tool, and a dry run of `raise_predicted_failure`, has been run against SAP's sandbox, on OData V2 and V4 services alike. The sandbox refuses writes, so creating notifications, orders and requisitions has been tested only against a simulated SAP service. Try document creation in a test client of your own system before you rely on it.

Every SuccessFactors tool has been run against SAP's SuccessFactors sandbox, which takes only an API key. Signing in as a technical user has been tested only against a simulated service.

## Next steps

- [MCP servers](/docs/connect/mcp-servers)
- [Secrets store](/docs/connect/secrets)
- [Microsoft Teams app](/docs/connect/teams)
- [Audit log](/docs/monitor/audit-log)

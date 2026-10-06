---
title: Connections
order: 3
summary: Per-user OAuth connections that let agents act as the signed-in person, and the connector sources that pull tickets in.
outcomes: Connect your own account to a service; Register a connection provider as an admin; Tell connections apart from connector sources
---

## Two kinds of connection

| | Connections | Connector sources |
| --- | --- | --- |
| Whose identity | Each user's own, via OAuth | A service account |
| Used for | Agents acting on your behalf | Pulling tickets and knowledge in |
| Where | **Connections** page | `/api/sources` |
| Examples | Salesforce, Microsoft Entra ID, Google, Jira | ServiceNow, Jira, IMAP, CSV, SQL |

## Connect your account

1. Open **Connections**. **Connected applications** lists what you have connected; **Available to connect** lists the rest.
2. Choose **Connect** on a service and approve the permissions it asks for.
3. Back in Liyagent, the row shows **Permissions asked**, **Permissions granted**, **Expiry** and **Last used**.
4. If a row says **Needs reconnecting**, the token expired or was revoked; choose **Connect** again.

Choose **Disconnect** (`DELETE /api/connections/{provider}`) to revoke it.

## Register a provider (admin)

Admins add the OAuth apps that users connect through on **Integrations setup**, picking from a catalogue of common providers (for example Google, Microsoft Entra ID, Okta, GitHub, Slack, Salesforce and Box) or entering one by hand. The page shows the **Callback URL to register at the provider**. Through the API: `GET /api/connections/providers` lists them and `PUT /api/connections/providers/{name}` saves one. `POST /api/connections/providers/discover` reads a provider's metadata from its issuer URL; `POST /api/connections/providers/register` registers dynamically where the provider allows it.

> [!NOTE]
> OAuth needs `TICKETIQ_PUBLIC_BASE_URL` so the provider can send users back to the right address.

## Connector sources

The built-in source types are `servicenow`, `jira`, `imap`, `eml`, `mbox`, `csv`, `sql_db`, `sqlite` and `erp_rest`. See [Jira](/docs/connect/jira), [ServiceNow](/docs/connect/servicenow), [ERP, SQL and file sources](/docs/connect/erp-sql) and [Email and SMTP](/docs/connect/email-smtp).

A source's credential (a Jira token, a ServiceNow, IMAP or database password, an ERP API token) belongs in the [secrets store](/docs/connect/secrets). Put `secret://<ID>` in the credential field, or pick the secret in the source form under **Settings** → **Data & retention**. The reference is opened only when the connector runs, never stored or returned resolved, and the secret's **Used by** lists the source. Saving refuses a reference to a missing secret (`422`), and naming a secret in a source takes `governance.write`. A value pasted directly still works and is masked on every read.

## Next steps

- [Secrets store](/docs/connect/secrets)
- [Salesforce](/docs/connect/salesforce)

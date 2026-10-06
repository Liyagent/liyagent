---
title: Identity and roles
order: 7
summary: How people, agents and clients sign in, how SSO and SCIM connect your directory, and how identities map to roles.
outcomes: Configure SSO with an identity provider; Provision users with SCIM; Explain the principal types the audit log records
---

## Principals

| Type | Who | Signs in with |
| --- | --- | --- |
| Human | People using the console | Password or SSO; a session cookie |
| Agent | Managed and self-managed agents | Agent credentials issued by Liyagent |
| Client | Integrations and OAuth clients | API key, client credentials |
| Service account | CI pipelines and the `liya` CLI | Client credentials, as the account it is bound to |

Audit rows record the actor and, where it is known, its type.

## Single sign-on

1. Set `TICKETIQ_PUBLIC_BASE_URL`; SSO won't start without it, except from the instance itself (loopback) during development.
2. Add an OpenID Connect provider on **Access** → **Single sign-on** (`PUT /api/auth/sso/{name}`), for example Microsoft Entra ID, with its authorization, token and userinfo URLs (https), client id and client secret.
3. Under **Roles from groups**, map directory groups to roles.
4. Under **New users**, choose **Existing accounts only** (the default) or **Create an account on first sign-in**, which requires a list of allowed email domains.
5. Test by signing in from `/login`. When it works, enforce SSO (`PUT /api/auth/sso-enforcement`) so passwords can no longer be used.

## SCIM

Provision and deprovision users and groups from your directory at `/scim/v2/Users` and `/scim/v2/Groups`; configure SCIM and issue its token on **Access** (`PUT /api/scim`, `POST /api/scim/token`). When the directory deprovisions a user, the account is disabled and its grants and sessions are ended; depending on the SCIM setting it is then deleted, unless it is the only owner of an agent.

## Service accounts

A service account is a CI pipeline's own credential, so a pipeline doesn't sign in with a person's password. It is bound to an existing account that has no password and whose role doesn't hold `*`, and every request made with it is that account's: its role, bindings and policies. It keeps working where SSO is enforced.

1. Under **Access** → **Users**, add an account with no password and a role holding only what the pipeline needs.
2. Open **Access** → **Service accounts** and choose **+ New service account**. Give it a name, pick the account, and set how many days the secret lasts (1 to 365, 90 by default).
3. Choose **Issue secret**. The `client_id` (`svc/<name>`) and the client secret are shown **once**, with a copy button: store the secret in your CI system's secret store straight away. Liyagent keeps only its hash.
4. The pipeline exchanges it at `POST /api/service-accounts/token` (client credentials) for a one-hour token, or passes `svc/<name>:<secret>` to `liya` ([Authentication](/docs/cli/authentication)).

The table lists each service account's name, the account and role it acts as, when it was created and by whom, when it was last used, when its secret expires, and its status. From a row's menu:

| Action | What it does | API |
| --- | --- | --- |
| **Rotate secret** | Issues a new secret, shown once. The old one stops working at once and the sessions it minted end; the expiry starts again. | `POST /api/service-accounts/{name}/rotate` |
| **Disable** / **Enable** | Disabling asks for a reason; the secret stops exchanging and its sessions end. Enabling restores it. | `PATCH /api/service-accounts/{name}` with `{"enabled": false, "reason": "..."}` |
| **Delete** | Asks for a reason, deletes the service account and ends its sessions. | `DELETE /api/service-accounts/{name}` with `{"reason": "..."}` |

Listing takes `access.read`; issuing, rotating, disabling, enabling and deleting take `access.write`. Issuing, rotating and enabling also take every permission the bound account holds, so nobody can hand out more than they have. Each action is in the audit log (`access.service_account.create`, `.rotate`, `.disable`, `.enable`, `.delete`), with its reason; the secret never is.

## Trusted issuers

To accept tokens from another identity provider (for example, an agent platform's workload identity), an owner adds a trusted issuer on **Access** → **Workload identity** → **+ Add trusted issuer**, and checks a sample with **Test token**.

## Next steps

- [Access](/docs/govern/access)
- [Tenancy](/docs/govern/tenancy)

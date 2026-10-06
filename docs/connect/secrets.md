---
title: Secrets store
order: 4
summary: Store each credential once, reference it everywhere as secret://ID, and optionally keep it in AWS Secrets Manager or HashiCorp Vault.
outcomes: Create a secret and reference it from a provider or trigger; Rotate a secret without touching what uses it; Use an external secret manager reference
---

## How it works

- A value is stored once under an **ID** and referenced as `secret://<ID>` (or `${secrets.<ID>}`). It is resolved at call time, never copied into the settings that use it.
- Values are sealed at rest with AES-256-GCM under a data key, which is wrapped by a local key, AWS KMS or Vault Transit.
- Values are write-only: the store shows each secret's ID, labels and what uses it, never the value.

## Create a secret

1. Open **Secrets store** and choose **+ Create secret**.

   | Field | Notes |
   | --- | --- |
   | ID | How resources refer to this value, for example `JIRA_API_TOKEN`. Letters, numbers, slashes, underscores and hyphens; it is uppercased and can't be changed later. |
   | Value | The secret itself, single line or multiline. Write-only. |
   | Labels | Optional key/value pairs for finding and filtering secrets. |

2. Choose **Create secret** (`POST /api/secret-store`).
3. Use it: in any credential field, enter `secret://JIRA_API_TOKEN`.

To rotate, choose **Update value** on the secret's row (`PATCH /api/secret-store/{id}`). Everything that references it uses the new value on its next call. **Delete** (`DELETE /api/secret-store/{id}`) lists what the secret is **Used by** first, since those references fail once it is gone.

> [!TIP]
> A provider key pasted in plain text can be moved into the store with `POST /api/llm/providers/{name}/externalize-key`.

## External secret managers

| Reference | Backend | Allow-list variable |
| --- | --- | --- |
| `secret://aws-sm/<name or ARN>[#key]` | AWS Secrets Manager | `TICKETIQ_SECRETS_AWS_SM_ALLOW` |
| `secret://hcv/<mount>/<path>#<field>` | HashiCorp Vault (KV version 2, or 1 with `TICKETIQ_SECRETS_HCV_KV_VERSION`) | `TICKETIQ_SECRETS_HCV_ALLOW` |

A value read from an external manager is held in memory for five minutes (`TICKETIQ_SECRETS_CACHE_SECONDS`) and never written to the store, so a secret rotated there is picked up within that time.

> [!WARNING]
> External references are off until their allow-list is set, so a reference can't be used to read an arbitrary secret the server's role can see.

## Next steps

- [Data handling](/docs/govern/data-handling)

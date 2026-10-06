---
title: Data handling
order: 4
summary: Where Liyagent keeps data, how it is encrypted, how long it stays and how it leaves.
outcomes: Name each data store and what it holds; Explain encryption at rest and per-tenant keys; Find the retention controls for each kind of record
---

## Where data lives

| Store | Holds |
| --- | --- |
| PostgreSQL (`TICKETIQ_DB_URL`, required) | The system of record: tickets, settings, users, audit log, usage, transcripts, the semantic cache |
| Vector store | Embeddings of tickets and knowledge for similarity search: embedded in the data directory by default, or a Qdrant server when `TICKETIQ_QDRANT_URL` is set |
| Data directory (`TICKETIQ_DATA_DIR`) | Attachment blobs, the local vault key file, the audit anchor and archive, and the embedded vector store |

The embedding model is baked into the image, so embeddings are computed on your own infrastructure. Model calls go only to the LLM providers you configure, and each provider has a **Data handling** section describing its terms. Other outbound traffic is what you connect: source systems, MCP servers, webhooks and integrations.

## Encryption

- Credentials (provider keys, connector passwords, people's OAuth tokens), signing keys and agent memory are sealed with AES-256-GCM. The data key is wrapped by a local key (`TICKETIQ_VAULT_KEY`, or a generated `vault.key` file in the data directory by default), AWS KMS (`TICKETIQ_VAULT_KMS_KEY_ID`) or HashiCorp Vault Transit (`TICKETIQ_VAULT_TRANSIT_KEY`).
- Content (transcript and session bodies, answer-record questions, attachment blobs) is sealed too only with `TICKETIQ_SEAL_CONTENT` on; it is off by default.
- With `TICKETIQ_TENANT_KEYS` on (off by default), each tenant gets its own data key. Retiring a tenant destroys its key, which crypto-shreds its sealed content; retirement needs both tenant keys and content sealing on. Rotate a tenant key with `POST /api/vault/tenants/{tenant_id}/rotate`.
- Cached answers are sealed with the tenant's key.

## Retention

| Record | Control |
| --- | --- |
| Audit log | **Keep rows for (days)** (`TICKETIQ_AUDIT_RETENTION_DAYS`, 365); older rows move to sealed archive segments; legal hold |
| Transcripts | Retention days (`TICKETIQ_TRANSCRIPT_RETENTION_DAYS`, 90), max conversations, legal hold |
| KB gap reports | `TICKETIQ_KB_GAP_RETENTION_DAYS` (90) |
| Semantic cache | Entry lifetime (`ttl_s`) |

## Egress

Outbound requests can be restricted by an egress policy (**Access** → **Egress**): ordered rules at organisation, agent and MCP server scope, in audit or enforce mode. Integration webhooks never reach link-local (cloud metadata) addresses, and `TICKETIQ_INTEGRATION_BLOCK_PRIVATE` (off by default) also stops them reaching private (RFC 1918) addresses.

> [!NOTE]
> For a DPIA, start from this page and the [Redaction](/docs/govern/redaction) page, and export the relevant audit rows as evidence.

## Next steps

- [Redaction](/docs/govern/redaction)
- [Tenancy](/docs/govern/tenancy)

---
title: GDPR and data protection
order: 8
summary: Who is controller and who is processor, how to answer a data-subject request with the console's tools, and the retention, residency, masking and audit evidence a DPIA asks for.
outcomes: Explain the controller and processor roles in a Liyagent deployment; Answer an access or erasure request across every store with a receipt; Find the retention, residency and redaction controls and the evidence each leaves
---

Liyagent keeps people's data in more places than a ticket table: the email a ticket came from, the conversation with an agent, the agent's memory, the spend ledger, the audit log. This page is the map for answering the GDPR (and UK GDPR, India's DPDP Act and the CCPA) on a deployment of it.

## Who is controller

| Deployment | Controller | Processor | Liyagent's role |
| --- | --- | --- | --- |
| Self-hosted, your own models | You | None needed from Liyagent | None: Liyagent never receives the data. The model providers, identity provider and connected systems you choose are your own processors. |
| Self-hosted, Liyagent support with access | You | Liyagent, for that access | Processor under the [Data Processing Addendum](/dpa) |
| Hosted pilot | You | Liyagent | Processor under the [Data Processing Addendum](/dpa), using the [sub-processors](/subprocessors) listed |

Your employees and customers are the data subjects. Your privacy notice tells them what the agents do with their data. Liyagent's own [privacy policy](/privacy) covers only Liyagent's website, demo and sales.

> [!NOTE]
> Agents on Teams and the other chat channels tell people they are an AI assistant. On the HR desk, sensitive HR matters are refused by a seeded guardrail, sent to your HR team and recorded as metadata only. No agent makes a decision with legal or similarly significant effect on its own. If you configure one to, Article 22 safeguards are yours to provide.

## Answer a data-subject request

The data-subject tools search, export and erase one person across **every store** Liyagent keeps, and name what they cannot reach on every result. The stores are tickets, pipeline runs, inbound email, attachments and their extracted text, knowledge articles, vectors, transcripts, sessions, agent-to-agent tasks, suspended runs, memory, answer records, the unanswered-question log, spans, the spend ledger, the audit log, the outbox, AI cases, policy samples and the public site's demo requests.

They need an administrator (`admin.write`) acting for every tenant, and a reason, which the audit row keeps with the person taken out of it.

1. **Search**: where the person is, by email, full name, external id or UPN. Counts and ids per store, never the content, and the legal holds that would block erasing them.

   ```bash
   curl -X POST https://ticketiq.example.com/api/privacy/search \
     -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d '{"email": "jane@example.com", "reason": "DSAR 2026-014"}'
   ```

2. **Export**: the access copy (Article 15) and portability copy (Article 20): every record that is theirs or names them, with content, as one JSON download. `POST /api/privacy/export` with the same body. The export is itself audited as a disclosure.
3. **Erase**: `POST /api/privacy/erase`. Their own records are deleted, mentions of them redacted to `[erased]`, their tickets pseudonymised (`"mode": "redact"`, the default) or deleted with everything derived from them (`"mode": "delete"`). Each store writes a receipt. A residual search runs from scratch and the job is `completed` only when it finds nothing.

Legal holds outrank erasure: a hold covering any match refuses the whole job before anything is touched. With `TICKETIQ_ERASURE_FOUR_EYES=true`, an erasure waits for a second administrator's approval (`POST /api/privacy/erasures/{id}/approve`).

The erasure register (`GET /api/privacy/erasures`) names each person only by a keyed digest and a masked hint. Each receipt carries its own digest, the job a digest over them all, and that digest is in the hash-chained audit log, so a receipt can be shown to be the one written at the time.

### What the tools do not reach

Every result lists it: sealed audit archive segments, backups, external knowledge sources, the source systems themselves, what webhooks and SIEM sinks already delivered, access records (console users, identity mappings, approvals, budgets and agent-registry entries naming a person, which you remove through access management), durable answer records, case-audit findings on tickets that were redacted rather than deleted, and the privacy requests the person sent through Liyagent's public site.

## The public site's privacy requests

On the Liyagent website, people use the [privacy request form](/privacy/request). Each request is stored, its address confirmed by a signed emailed link (or by an administrator, when outbound mail is not configured), and given a due date one month out. The **Privacy requests** queue in the operator view (on the instance that serves the public site, for its owner) lists them with what is overdue, runs search, export and erase against the requester's address once it is confirmed, and closes each with the answer given, optionally mailed. Every step is written on the request and audited against its reference.

## Retention

Each store has a window, set for the instance on `PUT /api/retention` and per tenant on the tenant, never below a floor (`TICKETIQ_RETENTION_FLOOR_DAYS`, 30 days by default) that the console can only raise. A daily purge applies them, and legal holds keep what they cover.

| Store | Default |
| --- | --- |
| Transcripts | 90 days (`TICKETIQ_TRANSCRIPT_RETENTION_DAYS`) |
| Pipeline runs | 365 days |
| Spans | 30 days (14 configured by `TICKETIQ_SPAN_RETENTION_DAYS`, held at the floor) |
| Answer records | 90 days |
| Tickets, attachments, memory | No age limit until you set one |
| Audit log | 365 days (`TICKETIQ_AUDIT_RETENTION_DAYS`), its own window and legal hold. Older rows move to sealed archive segments |
| Unanswered-question log | 90 days (`TICKETIQ_KB_GAP_RETENTION_DAYS`) |
| Demo requests (public site) | 730 days, with the client address blanked after 90 |
| Privacy requests (public site) | 1095 days after closing, with the client address blanked after 90 |

`POST /api/retention/purge` with `"dry_run": true` reports what a purge would delete and what holds keep.

## Residency and transfers

A tenant with a `residency_region` (an ISO code such as `DE`, or `EU`) has every model call and embedding kept in that geography, or refused. The region is computed from what the call goes to (a Bedrock or Vertex region, or the region attested on a provider record), and unknown is refused. `no_cross_geo` also refuses cross-region routing inside the geography. The embedding model runs inside Liyagent, so embeddings stay wherever the instance runs.

For transfers outside the EEA or UK under a hosted pilot, the [Data Processing Addendum](/dpa) incorporates the Standard Contractual Clauses (modules 2 and 3) and the UK Addendum.

## Masking personal data

Guardrails check every model input and output. A **Redact PII** rule masks identifiers (`[EMAIL]`) or tokenises them (`[EMAIL_1]`, stable for the whole conversation) so the model provider never sees them, and puts them back only in the answer the person reads and the tool calls made for them. See [Redaction](/docs/govern/redaction).

Transcript recording can be full, metadata only, or off, per agent.

## Evidence for a DPIA or an audit

- The audit log records administrative writes and agent calls. `GET /api/audit/verify` proves the chain is intact and `GET /api/audit/export` exports it.
- Erasure receipts and the erasure register show each request was carried out in full.
- `GET /api/retention` shows the windows in force, and the last purge's report shows what it deleted and held.
- [Data handling](/docs/govern/data-handling) lists the stores and how secrets and sensitive records are encrypted.

## Next steps

- [Data Processing Addendum](/dpa)
- [Sub-processors](/subprocessors)
- [Redaction](/docs/govern/redaction)
- [Tenancy](/docs/govern/tenancy)
